"""测试 services/rag/fallback.py：澄清 / 兜底 / followup。"""
from app.services.rag.fallback import (
    CLARIFY_THRESHOLD,
    build_clarify_frame,
    build_error_reply,
    build_followups,
    build_no_result_reply,
    build_rate_limited_reply,
    should_clarify,
)


# ===== should_clarify =====


def test_should_clarify_below_threshold():
    """分数低于阈值触发澄清。"""
    assert should_clarify(0.1) is True
    assert should_clarify(0.0) is True


def test_should_clarify_above_threshold():
    """分数高于阈值不澄清。"""
    assert should_clarify(0.5) is False
    assert should_clarify(1.0) is False


def test_should_clarify_boundary():
    """边界：等于阈值不澄清（< 而非 <=）。"""
    assert should_clarify(CLARIFY_THRESHOLD) is False


def test_should_clarify_custom_threshold():
    """自定义阈值。"""
    assert should_clarify(0.5, threshold=0.8) is True
    assert should_clarify(0.9, threshold=0.8) is False


# ===== build_clarify_frame =====


def test_clarify_frame_structure():
    """clarify 帧结构正确。"""
    frame = build_clarify_frame("怎么部署")
    assert frame["type"] == "clarify"
    assert "怎么部署" in frame["content"]
    assert isinstance(frame["options"], list)
    assert len(frame["options"]) == 3


def test_clarify_frame_custom_options():
    """自定义选项。"""
    opts = ["选项A", "选项B"]
    frame = build_clarify_frame("问题", options=opts)
    assert frame["options"] == opts


# ===== 兜底回复 =====


def test_no_result_reply():
    """无结果兜底包含引导。"""
    reply = build_no_result_reply()
    assert "没有检索到" in reply or "没有找到" in reply or "相关" in reply


def test_rate_limited_reply():
    """限流兜底提示等待。"""
    reply = build_rate_limited_reply()
    assert "限流" in reply or "频繁" in reply or "等待" in reply


def test_error_reply():
    """异常兜底提示重试。"""
    reply = build_error_reply()
    assert "异常" in reply or "重试" in reply or "稍后" in reply


# ===== build_followups =====


def test_followups_with_keyword():
    """有问题关键词时生成带关键词的追问。"""
    followups = build_followups("怎么部署应用", "部署步骤如下...")
    assert len(followups) >= 2
    # 关键词应被提取并出现在追问中
    assert any("部署" in f for f in followups)


def test_followups_no_keyword():
    """无法提取关键词时用通用模板。"""
    followups = build_followups("", "回答")
    assert len(followups) == 3
    assert any("展开" in f or "举例" in f or "相关" in f for f in followups)


def test_followups_strip_question_words():
    """剥除疑问词，保留核心词。"""
    # "怎么部署" → 剥除"怎么" → "部署"
    followups = build_followups("怎么部署", "")
    assert any("部署" in f for f in followups)
    # 不应把"怎么"作为关键词
    assert all("怎么" not in f for f in followups)


def test_followups_extract_longest_keyword():
    """多个候选时取最长的。"""
    followups = build_followups("配置文件，环境变量", "")
    # "配置文件" 和 "环境变量" 都是非停用词，取最长
    assert len(followups) >= 2
