"""澄清 / 拒答 / 降级 逻辑。"""
import re

from app.config import get_settings

#: 中文停用词 / 疑问词，用于 followup 关键词提取
_STOP_WORDS: set[str] = {
    "的", "了", "是", "在", "我", "你", "他", "她", "它", "们",
    "吗", "呢", "啊", "呀", "吧", "哦", "哈",
    "什么", "怎么", "怎样", "怎么样", "如何", "为什么", "为何",
    "是什么", "什么是", "哪", "哪里", "哪个",
    "请问", "请", "麻烦", "想", "知道", "了解", "一下",
    "有", "没有", "能", "不能", "可以", "不可", "会", "不会",
    "和", "与", "及", "或", "还有", "以及",
}

#: 标点 / 空白切分
_PUNCT_RE = re.compile(r"[，。？！,\.\?\!\s;；:：、]+")

#: 默认澄清选项
_DEFAULT_CLARIFY_OPTIONS = [
    "换一个更具体的关键词提问",
    "描述你想了解的应用场景",
    "提供相关的文章或频道范围",
]


def should_clarify(top_score: float, threshold: float | None = None) -> bool:
    """判断是否需要触发澄清（top rerank 分数低于阈值）。

    threshold 默认 None → 读 settings.rag_clarify_threshold（默认 0.1）。
    bge-reranker-v2-m3 对中文查询打分偏低，0.3 过严会误杀正常查询。
    """
    if threshold is None:
        threshold = get_settings().rag_clarify_threshold
    return top_score < threshold


def build_clarify_frame(question: str, options: list[str] | None = None) -> dict:
    """构造 clarify WS 帧。

    返回: {"type": "clarify", "content": "...", "options": [...]}
    content 引导用户选择想问的方向。
    如果未提供 options，给默认 3 个方向性选项。
    """
    opts = list(options) if options else list(_DEFAULT_CLARIFY_OPTIONS)
    content = (
        f"关于「{question}」，我目前把握不大。"
        "可以选择下面一个方向，或换一种提问方式："
    )
    return {"type": "clarify", "content": content, "options": opts}


def build_no_result_reply() -> str:
    """检索无结果时的兜底回复。"""
    return (
        "抱歉，当前知识库中没有检索到与你的问题相关的内容。"
        "可以尝试换个关键词，或描述得更具体一些。"
    )


def build_rate_limited_reply() -> str:
    """限流时的兜底回复。"""
    return "当前提问较为频繁，已触发限流。请稍作等待后再试。"


def build_error_reply() -> str:
    """LLM 异常时的降级回复。"""
    return "抱歉，回答生成过程中出现了异常。请稍后重试，或换一种方式提问。"


def build_followups(question: str, answer: str) -> list[str]:
    """生成推荐追问（P1 简化：基于问题关键词的模板，P3 接 LLM 生成）。

    返回 2-3 个追问候选。
    """
    keyword = _extract_keyword(question)
    if keyword:
        return [
            f"关于「{keyword}」，还有哪些值得了解的内容？",
            f"「{keyword}」在实际场景中如何应用？",
            f"能否举例说明「{keyword}」的关键点？",
        ]
    return [
        "能否进一步展开说明？",
        "还有哪些相关的内容值得了解？",
        "能否举一个具体的例子？",
    ]


def _extract_keyword(question: str) -> str:
    """从问题中提取核心关键词（去除疑问词与停用词）。

    按标点 / 空白切分后：
    - 过滤纯停用词 token；
    - 对剩余 token 剥除前导 / 尾随的停用词片段（如「怎么部署」→「部署」）；
    取最长的非空结果；若全部被过滤则返回空串，由调用方走通用模板。
    """
    if not question:
        return ""
    parts = [p.strip() for p in _PUNCT_RE.split(question) if p.strip()]
    candidates: list[str] = []
    for p in parts:
        if p in _STOP_WORDS:
            continue
        cleaned = _strip_stop_words(p)
        if cleaned:
            candidates.append(cleaned)
    if not candidates:
        return ""
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def _strip_stop_words(token: str) -> str:
    """剥除 token 前后缀中出现的停用词片段，保留中间核心词。"""
    s = token
    changed = True
    while changed:
        changed = False
        for w in _STOP_WORDS:
            if len(s) <= len(w):
                continue
            if s.startswith(w):
                s = s[len(w):]
                changed = True
            elif s.endswith(w):
                s = s[: -len(w)]
                changed = True
    return s.strip()
