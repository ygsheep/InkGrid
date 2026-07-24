"""Q&A 生成：文章入库后 LLM 自动生成问题+答案对。

流程：
1. 读取文章标题 + 正文（markdown）
2. LLM 生成 3-5 个 Q&A（JSON 结构化输出）
3. 写入 PG qa_pairs (status=pending) 供前端审核
"""
import json
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.crud import qa as qa_crud
from app.models.post import Post
from app.services.llm.base import BaseLLMProvider

logger = get_logger("qa.generator")

#: 生成 Q&A 数量
QA_COUNT = 5

#: 生成 Q&A 的 system prompt
_QA_SYSTEM_PROMPT = """你是一位技术内容分析专家。你的任务是阅读文章并生成读者可能会问的问题及其答案。

要求：
1. 生成 {count} 个高质量的问题-答案对
2. 问题应覆盖文章的核心概念、实际应用、常见疑问
3. 答案应基于文章内容，简洁准确，不编造信息
4. 问题用自然语言表述（如用户真实提问的口吻）
5. 答案控制在 200 字以内

输出格式（严格 JSON，不要包裹在 markdown 代码块中）：
[
  {{"question": "问题文本", "answer": "答案文本"}},
  ...
]
"""

#: user prompt 模板
_QA_USER_TEMPLATE = """# 文章标题
{title}

# 文章内容
{content}

请基于以上文章生成 {count} 个问题-答案对。"""


async def generate_qa_for_article(db: AsyncSession, post_id: UUID) -> int:
    """为文章生成 Q&A 对，写入 PG (status=pending)。

    Returns:
        生成的 Q&A 数量
    """
    # 1. 加载文章
    stmt = select(Post).where(Post.id == post_id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if not post:
        raise ValueError(f"post {post_id} not found")

    # 2. 构造 LLM 调用
    provider = BaseLLMProvider()
    client: AsyncOpenAI = provider.create_client()

    system_prompt = _QA_SYSTEM_PROMPT.format(count=QA_COUNT)
    user_prompt = _QA_USER_TEMPLATE.format(
        title=post.title,
        content=post.content_md[:6000],  # 截断防止超长
        count=QA_COUNT,
    )

    logger.info("qa_generation_start", post_id=str(post_id), title=post.title)

    # 3. 调用 LLM（非流式，JSON 输出）
    resp = await client.chat.completions.create(
        model=provider.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content or "[]"

    # 4. 解析 JSON
    try:
        qa_list = _parse_qa_json(raw)
    except Exception as e:
        logger.error("qa_parse_failed", post_id=str(post_id), raw=raw[:500], error=str(e))
        return 0

    if not qa_list:
        logger.warning("qa_empty", post_id=str(post_id))
        return 0

    # 5. 写入 PG
    created = 0
    for item in qa_list:
        question = (item.get("question") or "").strip()
        answer = (item.get("answer") or "").strip()
        if not question or not answer:
            continue
        await qa_crud.create(
            db,
            article_id=post_id,
            question=question,
            answer=answer,
            status="pending",
        )
        created += 1

    logger.info("qa_generation_done", post_id=str(post_id), count=created)
    return created


def _parse_qa_json(raw: str) -> list[dict]:
    """解析 LLM 返回的 Q&A JSON。

    LLM 可能返回裸数组或 {"qa": [...]} 格式，统一处理。
    """
    text = raw.strip()
    # 去除可能的 markdown 代码块包裹
    if text.startswith("```"):
        lines = text.split("\n")
        # 去首尾 ``` 行
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    data = json.loads(text)
    # 兼容 {"qa": [...]} 或 {"items": [...]} 或裸数组
    if isinstance(data, dict):
        for key in ("qa", "items", "data", "questions"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
    if isinstance(data, list):
        return data
    return []
