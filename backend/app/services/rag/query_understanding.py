"""Query Understanding：1 次 LLM 结构化输出，提取关键词 + 意图 + 路由。

设计参考：plan/后端设计方案.md §6.7
- 合并原 Round 1（关键词拆解）+ Round 2（意图提取）为一次调用
- 用小/快模型即可，输出 JSON
- 路由结果驱动后续检索策略（FAQ 优先 / RAG / channel / external）
"""
import json
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from app.core.logging import get_logger
from app.services.llm.base import BaseLLMProvider

logger = get_logger("rag.query_understanding")

#: 路由类型
ROUTE_FAQ_FIRST = "faq_first"
ROUTE_RAG = "rag"
ROUTE_CHANNEL = "channel"
ROUTE_EXTERNAL = "external_tool"

#: FAQ 短路阈值（rerank 分数高于此值时直接用 FAQ 答案）
FAQ_SHORT_CIRCUIT_THRESHOLD = 0.8

#: Query Understanding system prompt
_QP_SYSTEM_PROMPT = """你是一个查询理解引擎。分析用户的问题，提取关键信息，输出结构化 JSON。

任务：
1. keywords: 提取 2-5 个核心关键词，用于增强向量检索
2. intent: 一句话描述用户意图（如"用户想了解部署方式和注意事项"）
3. route: 根据问题特征判断检索策略：
   - "faq_first": 简单事实性问题（如"XX是什么"、"如何配置XX"），FAQ 库可能直接命中
   - "rag": 需要深入理解文章内容的问题（如"XX和YY的区别"、"详细方案"）
   - "channel": 用户明确提到某个频道/分类范围
   - "external_tool": 需要外部工具（如实时搜索、计算）——暂留

输出格式（严格 JSON，不要 markdown 代码块）：
{"keywords": ["关键词1", "关键词2"], "intent": "意图描述", "route": "faq_first"}"""

#: user prompt 模板
_QP_USER_TEMPLATE = "用户问题：{query}"


@dataclass
class QueryAnalysis:
    """查询理解结果。"""

    keywords: list[str] = field(default_factory=list)
    intent: str = ""
    route: str = ROUTE_RAG
    enhanced_query: str = ""
    """增强检索用查询（原始 query + keywords 拼接）"""


async def analyze_query(query: str) -> QueryAnalysis:
    """1 次 LLM 调用，提取关键词 + 意图 + 路由。

    LLM 不可用时降级为简单分词（不阻断流程）。
    """
    provider = BaseLLMProvider()
    client: AsyncOpenAI = provider.create_client()

    system_prompt = _QP_SYSTEM_PROMPT
    user_prompt = _QP_USER_TEMPLATE.format(query=query)

    try:
        resp = await client.chat.completions.create(
            model=provider.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        result = _parse_json(raw)

        keywords = result.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = [str(keywords)]

        intent = result.get("intent", "")
        route = result.get("route", ROUTE_RAG)
        if route not in (ROUTE_FAQ_FIRST, ROUTE_RAG, ROUTE_CHANNEL, ROUTE_EXTERNAL):
            route = ROUTE_RAG

        # 增强查询：原始 query + keywords 拼接（用于 embedding 检索）
        enhanced = query
        if keywords:
            kw_str = " ".join(keywords)
            enhanced = f"{query} {kw_str}"

        logger.info(
            "query_analyzed",
            query=query[:50],
            keywords=keywords,
            intent=intent[:80],
            route=route,
        )
        return QueryAnalysis(
            keywords=keywords,
            intent=intent,
            route=route,
            enhanced_query=enhanced,
        )

    except Exception as e:
        logger.warning("query_understanding_fallback", query=query[:50], error=str(e))
        # 降级：直接用原始 query 做 RAG
        return QueryAnalysis(
            keywords=[],
            intent=query,
            route=ROUTE_RAG,
            enhanced_query=query,
        )


def _parse_json(raw: str) -> dict:
    """解析 LLM 返回的 JSON，容错处理。"""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
