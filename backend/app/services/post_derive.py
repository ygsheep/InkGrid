"""文章派生字段自动生成:excerpt / reading_time / toc / slug。

在文章创建/更新时,若未显式提供这些字段,则从 title/content_md 自动生成。
"""
import re

from app.ingest.parser import parse_markdown
from app.ingest.toc import headings_to_toc
from app.utils.slug import slugify

#: 摘要最大长度
EXCERPT_MAX_LENGTH = 200

#: 阅读速度:中文字符每分钟
CPM_CHINESE = 400

#: 阅读速度:英文单词每分钟
WPM_ENGLISH = 220


def generate_excerpt(content_md: str, max_len: int = EXCERPT_MAX_LENGTH) -> str:
    """从 Markdown 内容提取首段非标题文本作为摘要。

    规则:
    1. 跳过标题行(# 开头)
    2. 跳过空行
    3. 取第一个有内容的段落
    4. 去除 Markdown 标记(**、`、链接、图片等)
    5. 截断到 max_len
    """
    if not content_md:
        return ""

    lines = content_md.splitlines()
    first_paragraph_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        # 跳过空行(如果还没开始收集,继续;如果已在收集,段落结束)
        if not stripped:
            if first_paragraph_lines:
                break
            continue
        # 跳过标题
        if re.match(r"^#{1,6}\s+", stripped):
            continue
        # 跳过纯 HTML 注释或 frontmatter
        if stripped.startswith("<!--") or stripped.startswith("---"):
            continue
        # 跳过纯图片行(去除图片标记后为空的行)
        if not re.sub(r"!\[[^\]]*\]\([^)]+\)", "", stripped).strip():
            continue
        first_paragraph_lines.append(stripped)

    if not first_paragraph_lines:
        return ""

    text = " ".join(first_paragraph_lines)

    # 去除 Markdown 标记
    # 图片 ![alt](url) → 移除(不保留 alt,避免图片描述污染摘要)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # 链接 [text](url)
    text = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # 粗体/斜体 **text** / *text* / __text__ / _text_
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # 行内代码 `code`
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 引用标记 >
    text = re.sub(r"^>\s*", "", text)
    # 列表标记 - / * / 1.
    text = re.sub(r"^[\-\*\+]\s+", "", text)
    text = re.sub(r"^\d+\.\s+", "", text)
    # 多余的空白
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def calculate_reading_time(content_md: str) -> int:
    """估算阅读时长(分钟)。

    中文按字符数 / CPM_CHINESE,英文按词数 / WPM_ENGLISH,取两者之和向上取整。
    """
    if not content_md:
        return 1

    # 去掉 Markdown 标记,只统计正文
    text = content_md
    # 去掉代码块
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 去掉行内代码
    text = re.sub(r"`[^`]+`", "", text)
    # 去掉图片和链接,保留文本
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # 去掉标题标记
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # 中文字符数
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    # 英文词数(去掉中文后按空白分词)
    non_chinese = re.sub(r"[\u4e00-\u9fff]", " ", text)
    english_words = len([w for w in non_chinese.split() if w])

    minutes = (chinese_chars / CPM_CHINESE) + (english_words / WPM_ENGLISH)
    return max(1, int(minutes) + (1 if minutes % 1 > 0 else 0))


def generate_toc(content_md: str) -> list[dict]:
    """从 Markdown 内容生成目录(TOC)。"""
    if not content_md:
        return []
    parsed = parse_markdown(title="", content_md=content_md)
    return headings_to_toc(parsed.headings)


def derive_slug(title: str) -> str:
    """从标题生成 slug(封装 slugify)。"""
    return slugify(title) or "untitled"
