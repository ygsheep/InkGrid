"""slug 生成:标题 → URL 友好标识。

P0 简化:不做中文转拼音,中文字符原样保留(通过冲突后缀保证唯一)。
如需更友好的纯 ASCII slug,后续可引入 python-slugify(已在 rag 可选依赖中)。
"""
import re

#: Post.slug 字段长度上限
MAX_SLUG_LENGTH = 120


def slugify(text: str) -> str:
    """把任意文本转为 URL 友好的 slug。

    规则:
    1. 转小写
    2. 非 [a-z0-9\\u4e00-\\u9fff] 字符替换为连字符
    3. 合并连续连字符
    4. 去除首尾连字符
    5. 截断到 MAX_SLUG_LENGTH
    """
    if not text:
        return ""
    # 转小写
    s = text.lower()
    # 非 ASCII 字母/数字/中文(基本区)替换为连字符
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    # 去除首尾连字符
    s = s.strip("-")
    # 截断
    if len(s) > MAX_SLUG_LENGTH:
        s = s[:MAX_SLUG_LENGTH].rstrip("-")
    return s
