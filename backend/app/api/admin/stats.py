"""数据看板：聚合 stats + 问答明细 + 最近问答列表。

聚合接口单次返回看板所需的全部数据，避免前端发 N 次请求。
数据源：posts / chat_messages / chat_sessions / knowledge_docs / personas。
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from app.deps import AdminId, DBSession
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge import KnowledgeDoc
from app.models.persona import Persona
from app.models.post import Post
from app.models.channel import Channel
from app.schemas.common import Page, envelope
from app.schemas.stats import (
    QuestionStatItem,
    RecentQuestion,
    StatsOverview,
    StatsSummary,
    StatsTrend,
    TopArticle,
    TopQuestion,
)

router = APIRouter(prefix="/stats")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(days: int) -> datetime:
    return _now() - timedelta(days=days)


async def _fetch_summary(db) -> StatsSummary:
    """看板顶部 4 个卡片指标。"""
    # 已发布文章数
    post_count = await db.scalar(
        select(func.count(Post.id)).where(Post.status == "published")
    )
    # 问答次数（chat_messages.role='user'）
    question_count = await db.scalar(
        select(func.count(ChatMessage.id)).where(ChatMessage.role == "user")
    )
    # 知识库文档数（全部 status）
    doc_count = await db.scalar(select(func.count(KnowledgeDoc.id)))
    # 本月访问：P0 估算 = 本月新增 chat_sessions + 本月新发 posts
    month_start = _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_sessions = await db.scalar(
        select(func.count(ChatSession.id)).where(ChatSession.created_at >= month_start)
    )
    new_posts = await db.scalar(
        select(func.count(Post.id)).where(Post.published_at >= month_start)
    )
    return StatsSummary(
        postCount=post_count or 0,
        questionCount=question_count or 0,
        knowledgeDocCount=doc_count or 0,
        monthlyViews=(new_sessions or 0) + (new_posts or 0),
    )


async def _fetch_trend(db) -> StatsTrend:
    """近 7 天每日趋势。用 generate_series 保证空日期补 0。"""
    start = _days_ago(6).replace(hour=0, minute=0, second=0, microsecond=0)
    # 文章趋势
    posts_sql = text(
        """
        SELECT d::date AS day, COUNT(p.id) AS cnt
        FROM generate_series(:start, :end, '1 day'::interval) d
        LEFT JOIN posts p ON p.published_at::date = d::date
                              AND p.status = 'published'
        GROUP BY d::date ORDER BY d::date
        """
    )
    posts_rows = (await db.execute(posts_sql, {"start": start, "end": _now()})).all()
    posts_trend = [int(r[1] or 0) for r in posts_rows]

    # 问答趋势
    q_sql = text(
        """
        SELECT d::date AS day, COUNT(m.id) AS cnt
        FROM generate_series(:start, :end, '1 day'::interval) d
        LEFT JOIN chat_messages m ON m.created_at::date = d::date
                                     AND m.role = 'user'
        GROUP BY d::date ORDER BY d::date
        """
    )
    q_rows = (await db.execute(q_sql, {"start": start, "end": _now()})).all()
    questions_trend = [int(r[1] or 0) for r in q_rows]

    return StatsTrend(posts=posts_trend, questions=questions_trend)


async def _fetch_top_articles(db) -> list[TopArticle]:
    """热门文章 Top 5（按引用次数降序）。

    chat_messages.citations 是 JSONB 数组，元素含 articleId 字段。
    用 jsonb_array_elements 展开后 group + count。
    """
    # 用子查询先过滤掉 citations 为 null 或非数组的行，
    # 否则 jsonb_array_elements 在标量行上会抛 cannot extract elements from a scalar
    sql = text(
        """
        SELECT c->>'articleId' AS article_id, COUNT(*) AS cnt
        FROM (
            SELECT citations FROM chat_messages
            WHERE citations IS NOT NULL
              AND jsonb_typeof(citations) = 'array'
        ) AS m, jsonb_array_elements(m.citations) AS c
        WHERE c->>'articleId' IS NOT NULL
        GROUP BY c->>'articleId'
        ORDER BY cnt DESC
        LIMIT 5
        """
    )
    rows = (await db.execute(sql)).all()
    if not rows:
        return []
    # 一次查所有文章（避免 N+1）
    article_ids = [r[0] for r in rows if r[0]]
    if not article_ids:
        return []
    # 用 PostgreSQL 的 = ANY 查询
    articles_q = select(Post, Channel.name).join(
        Channel, Post.channel_id == Channel.id, isouter=True
    ).where(Post.id.in_([UUID(a) for a in article_ids if a]))
    article_rows = (await db.execute(articles_q)).all()
    article_map = {str(p.id): (p, channel_name) for p, channel_name in article_rows}
    result = []
    for r in rows:
        aid = r[0]
        if aid and aid in article_map:
            p, channel_name = article_map[aid]
            result.append(
                TopArticle(
                    slug=p.slug,
                    title=p.title,
                    channelName=channel_name,
                    citationCount=int(r[1]),
                )
            )
    return result


async def _fetch_top_questions(db) -> list[TopQuestion]:
    """热门问题 Top 5（按出现次数降序，简单 group by content 前 100 字）。"""
    sql = text(
        """
        SELECT LEFT(content, 100) AS q, COUNT(*) AS cnt
        FROM chat_messages
        WHERE role = 'user'
        GROUP BY LEFT(content, 100)
        ORDER BY cnt DESC
        LIMIT 5
        """
    )
    rows = (await db.execute(sql)).all()
    return [TopQuestion(content=r[0], count=int(r[1])) for r in rows]


async def _fetch_recent_questions(db, limit: int = 10) -> list[RecentQuestion]:
    """最近 N 条问答会话。

    关联 personas.name 取角色名；子查询取每会话首问 + 末答 + 消息数。
    """
    sql = text(
        """
        SELECT
            s.id AS session_id,
            s.title AS session_title,
            p.name AS persona_name,
            s.scope_type,
            s.scope_ref,
            s.created_at,
            (
                SELECT content FROM chat_messages
                WHERE session_id = s.id AND role = 'user'
                ORDER BY created_at ASC LIMIT 1
            ) AS first_question,
            (
                SELECT content FROM chat_messages
                WHERE session_id = s.id AND role = 'assistant'
                ORDER BY created_at DESC LIMIT 1
            ) AS last_answer,
            (
                SELECT COUNT(*) FROM chat_messages WHERE session_id = s.id
            ) AS msg_count
        FROM chat_sessions s
        LEFT JOIN personas p ON s.persona_id = p.id
        ORDER BY s.created_at DESC
        LIMIT :limit
        """
    )
    rows = (await db.execute(sql, {"limit": limit})).all()
    return [
        RecentQuestion(
            sessionId=str(r[0]),
            title=r[1],
            personaName=r[2],
            scopeType=r[3],
            scopeRef=r[4],
            firstQuestion=(r[6][:200] if r[6] else None),
            lastAnswerSnippet=(r[7][:80] if r[7] else None),
            messageCount=int(r[8] or 0),
            createdAt=r[5],
        )
        for r in rows
    ]


@router.get("/overview")
async def get_overview(db: DBSession, _: AdminId) -> dict:
    """看板聚合：单次返回看板所需全部数据。

    一次 DB 会话并行 5 个聚合查询，目标 P95 < 200ms。
    Redis 缓存后续 P3 加（先保证功能可用）。
    """
    summary = await _fetch_summary(db)
    trend = await _fetch_trend(db)
    top_articles = await _fetch_top_articles(db)
    top_questions = await _fetch_top_questions(db)
    recent = await _fetch_recent_questions(db)
    data = StatsOverview(
        summary=summary,
        trend=trend,
        topArticles=top_articles,
        topQuestions=top_questions,
        recentQuestions=recent,
    )
    return envelope(data.model_dump())


@router.get("/questions")
async def list_question_stats(
    db: DBSession,
    _: AdminId,
    group_by: str = Query("scope", regex="^(scope|persona|date)$"),
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict:
    """问答明细按维度聚合。

    - group_by=scope：按 scope_type:scope_ref 分组
    - group_by=persona：按 personas.name 分组
    - group_by=date：按 created_at::date 分组
    """
    date_to = date_to or _now()
    date_from = date_from or _days_ago(30)

    if group_by == "scope":
        dim_expr = func.concat(
            ChatSession.scope_type, ":",
            func.coalesce(ChatSession.scope_ref, ""),
        )
    elif group_by == "persona":
        dim_expr = func.coalesce(Persona.name, "(无角色)")
    else:  # date
        dim_expr = func.date(ChatMessage.created_at)

    stmt = (
        select(
            dim_expr.label("dimension"),
            func.count(ChatMessage.id).label("question_count"),
            func.avg(ChatMessage.latency_ms).label("avg_latency"),
            func.max(ChatMessage.created_at).label("last_active"),
        )
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id, isouter=True)
        .join(Persona, ChatSession.persona_id == Persona.id, isouter=True)
        .where(ChatMessage.role == "user")
        .where(ChatMessage.created_at >= date_from)
        .where(ChatMessage.created_at <= date_to)
        .group_by(dim_expr)
        .order_by(func.count(ChatMessage.id).desc())
    )

    # 分页（先 count 再 limit）
    count_stmt = (
        select(func.count())
        .select_from(stmt.subquery())
    )
    total = await db.scalar(count_stmt)
    offset = (page - 1) * size
    rows = (await db.execute(stmt.offset(offset).limit(size))).all()

    items = [
        QuestionStatItem(
            dimension=str(r[0] or "(未知)"),
            questionCount=int(r[1] or 0),
            avgLatencyMs=int(r[2]) if r[2] is not None else None,
            lastActiveAt=r[3],
        )
        for r in rows
    ]
    page_obj = Page[QuestionStatItem](
        items=items, total=total or 0, page=page, size=size
    )
    return envelope(page_obj.model_dump())


@router.get("/recent-questions")
async def list_recent_questions(
    db: DBSession,
    _: AdminId,
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """最近问答列表（独立端点，便于前端只刷最近问答不重拉指标）。"""
    items = await _fetch_recent_questions(db, limit=limit)
    page_obj = Page[RecentQuestion](
        items=items, total=len(items), page=1, size=limit
    )
    return envelope(page_obj.model_dump())
