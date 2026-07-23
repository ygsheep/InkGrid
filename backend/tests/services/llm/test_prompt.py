"""测试 services/llm/prompt.py：系统提示词构建。"""
from datetime import date

from app.services.llm.prompt import build_system_prompt


def test_prompt_contains_persona_name():
    """提示词包含人设名称。"""
    prompt = build_system_prompt(
        persona_name="小墨",
        persona_system_prompt="你是一位技术助手。",
        scope_type="global",
        scope_ref="",
        current_date="2026-07-23",
    )
    assert "小墨" in prompt


def test_prompt_default_persona_when_empty():
    """人设名为空时用兜底名称。"""
    prompt = build_system_prompt(
        persona_name="",
        persona_system_prompt="",
        scope_type="global",
        scope_ref="",
        current_date="2026-07-23",
    )
    assert "AI 助手" in prompt or "AI问答助手" in prompt


def test_prompt_contains_scope_description():
    """提示词包含范围描述。"""
    prompt = build_system_prompt(
        persona_name="助手",
        persona_system_prompt="",
        scope_type="channel",
        scope_ref="policy",
        current_date="2026-07-23",
    )
    assert "频道" in prompt
    assert "policy" in prompt


def test_prompt_global_scope():
    """global 范围描述。"""
    prompt = build_system_prompt(
        persona_name="助手",
        persona_system_prompt="",
        scope_type="global",
        scope_ref="",
        current_date="2026-07-23",
    )
    assert "全站" in prompt or "全部文章" in prompt


def test_prompt_article_scope():
    """article 范围描述。"""
    prompt = build_system_prompt(
        persona_name="助手",
        persona_system_prompt="",
        scope_type="article",
        scope_ref="my-post",
        current_date="2026-07-23",
    )
    assert "文章" in prompt
    assert "my-post" in prompt


def test_prompt_contains_current_date():
    """提示词包含当前日期（时效性）。"""
    prompt = build_system_prompt(
        persona_name="助手",
        persona_system_prompt="",
        scope_type="global",
        scope_ref="",
        current_date="2026-07-23",
    )
    assert "2026-07-23" in prompt


def test_prompt_date_object_accepted():
    """date 对象作为 current_date。"""
    prompt = build_system_prompt(
        persona_name="助手",
        persona_system_prompt="",
        scope_type="global",
        scope_ref="",
        current_date=date(2026, 7, 23),
    )
    assert "2026-07-23" in prompt


def test_prompt_contains_citation_rules():
    """提示词包含引用规范 [n]。"""
    prompt = build_system_prompt(
        persona_name="助手",
        persona_system_prompt="",
        scope_type="global",
        scope_ref="",
        current_date="2026-07-23",
    )
    assert "[1]" in prompt or "[n]" in prompt or "引用" in prompt


def test_prompt_contains_refusal_guidance():
    """提示词包含拒答引导（不编造）。"""
    prompt = build_system_prompt(
        persona_name="助手",
        persona_system_prompt="自定义口吻。",
        scope_type="global",
        scope_ref="",
        current_date="2026-07-23",
    )
    assert "编造" in prompt or "拒绝" in prompt or "无法" in prompt
    assert "自定义口吻" in prompt
