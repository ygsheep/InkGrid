"""双链关系 CRUD + 解析。

解析 content_md 中的 [[标题]] 双链（排除 ![[嵌入]]），重建出链。
- target_title_raw：[[ ]] 内的原始文本（取 | 或 # 之前的部分）
- target_note_id：按 title 精确匹配 Post，命中则填充，否则为空（悬空链接）
"""
import re
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note_link import NoteLink
from app.models.post import Post

# 匹配 [[标题]]，但不匹配 ![[嵌入]]（前面不是 !）
# 支持 [[标题|别名]] 与 [[标题#锚点]]，取 | 或 # 之前部分
_LINK_RE = re.compile(r"(?<!!)\[\[([^\]]+?)\]\]")


def extract_link_titles(content_md: str) -> list[str]:
    """从 Markdown 内容提取双链目标标题（去重保序）。"""
    titles: list[str] = []
    seen: set[str] = set()
    for m in _LINK_RE.finditer(content_md or ""):
        raw = m.group(1)
        # 取 | 或 # 之前部分
        title = re.split(r"[|#]", raw, 1)[0].strip()
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


async def sync_links(
    db: AsyncSession,
    source_note_id: UUID,
    content_md: str,
) -> list[NoteLink]:
    """重建某笔记的出链关系。

    - 先删除该 source 的所有旧链接
    - 解析 content_md 提取双链标题
    - 按 title 匹配 Post 填充 target_note_id（命中则链接，未命中则悬空）
    返回新建的 NoteLink 列表。
    """
    # 1. 清理旧出链
    await db.execute(
        delete(NoteLink).where(NoteLink.source_note_id == source_note_id)
    )
    await db.flush()

    # 2. 解析双链
    titles = extract_link_titles(content_md)
    if not titles:
        return []

    # 3. 批量按 title 匹配笔记（仅匹配现有笔记，不限 category）
    #    注意：同 title 可能有多篇，取第一篇（按 created_at 升序）
    stmt = (
        select(Post.id, Post.title)
        .where(Post.title.in_(titles))
        .order_by(Post.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    title_to_id: dict[str, UUID] = {}
    for row in rows:
        t = row.title
        if t not in title_to_id:  # 保留最早的一篇
            title_to_id[t] = row.id

    # 4. 插入新链接
    new_links: list[NoteLink] = []
    for title in titles:
        link = NoteLink(
            source_note_id=source_note_id,
            target_note_id=title_to_id.get(title),
            target_title_raw=title,
        )
        db.add(link)
        new_links.append(link)
    await db.flush()
    return new_links


async def list_outgoing(
    db: AsyncSession,
    source_note_id: UUID,
) -> list[NoteLink]:
    """列出某笔记的出链。"""
    stmt = select(NoteLink).where(NoteLink.source_note_id == source_note_id)
    return list((await db.execute(stmt)).scalars().all())


async def list_backlinks(
    db: AsyncSession,
    target_note_id: UUID,
) -> list[tuple[NoteLink, Post]]:
    """列出引用某笔记的所有反链（含来源笔记信息）。

    返回 [(link, source_post), ...]。
    匹配条件：target_note_id 命中（精确链接）。
    """
    stmt = (
        select(NoteLink, Post)
        .join(Post, Post.id == NoteLink.source_note_id)
        .where(NoteLink.target_note_id == target_note_id)
        .order_by(NoteLink.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows]


async def resolve_dangling_links(
    db: AsyncSession,
    note_id: UUID,
    note_title: str,
) -> int:
    """笔记新建/改标题后，把指向该标题的悬空链接回填为 target_note_id。

    返回更新的链接数。
    """
    # 找到 target_title_raw == note_title 且 target_note_id 为空的链接
    stmt = select(NoteLink).where(
        NoteLink.target_title_raw == note_title,
        NoteLink.target_note_id.is_(None),
        NoteLink.source_note_id != note_id,  # 排除自引用
    )
    links = list((await db.execute(stmt)).scalars().all())
    for link in links:
        link.target_note_id = note_id
        db.add(link)
    if links:
        await db.flush()
    return len(links)
