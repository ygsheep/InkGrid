"""TOC(目录)生成:从 ParsedDoc.headings 生成前端 TocItem 列表。

TocItem 契约(与 schemas/post.py 对齐):
    {id: str, title: str, level: int}

- id:由 title 经 slugify 生成,用作 HTML 锚点
- title:保留原标题原文
- level:1-6
- 重复 id 自动加 -2/-3 后缀保证唯一
"""
from app.utils.slug import slugify


def headings_to_toc(headings: list[dict]) -> list[dict]:
    """把 parser 的 headings 转为 TocItem 列表。

    Args:
        headings: parse_markdown 返回的 [{level, text, position}, ...]

    Returns:
        [{id, title, level}, ...]
    """
    toc: list[dict] = []
    seen_ids: dict[str, int] = {}  # id → 已出现次数

    for h in headings:
        title = h["text"]
        level = h["level"]
        base_id = slugify(title) or "heading"

        # 唯一化:第二次出现加 -2,第三次 -3...
        count = seen_ids.get(base_id, 0)
        seen_ids[base_id] = count + 1
        if count == 0:
            final_id = base_id
        else:
            final_id = f"{base_id}-{count + 1}"

        toc.append({"id": final_id, "title": title, "level": level})

    return toc
