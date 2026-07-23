"""文件上传安全验证。

策略(纵深防御,任一失败即拒绝):
1. 文件名:basename 化(防路径遍历)、长度限制、非空
2. 扩展名:白名单 .md(大小写不敏感)
3. MIME 类型:白名单 text/markdown | text/plain | text/x-markdown | application/octet-stream
4. 大小:上限 MAX_FILE_SIZE
5. 内容嗅探:拒绝 NUL 字节(防二进制伪装)
6. 编码:严格 UTF-8 解码
"""
import re

from fastapi import UploadFile

#: 允许的扩展名(小写,含点)
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".md"})

#: 允许的 MIME 类型
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "text/markdown",
        "text/plain",
        "text/x-markdown",
        "application/octet-stream",  # 浏览器兜底
    }
)

#: 文件大小上限:5 MB
MAX_FILE_SIZE: int = 5 * 1024 * 1024

#: 文件名长度上限(含扩展名)
MAX_FILENAME_LENGTH: int = 200


class UploadSecurityError(Exception):
    """文件上传安全校验失败。"""


def validate_filename(filename: str | None) -> str:
    """校验文件名,返回安全的 basename。

    - 去除路径分隔符(防路径遍历)
    - 非空校验
    - 长度限制
    """
    if not filename or not filename.strip():
        raise UploadSecurityError("文件名不能为空")

    # basename 化:同时处理 / 和 \ (Windows)
    safe = re.split(r"[\\/]", filename)[-1].strip()

    if not safe:
        raise UploadSecurityError("文件名不能为空")

    if len(safe) > MAX_FILENAME_LENGTH:
        raise UploadSecurityError(f"文件名过长(>{MAX_FILENAME_LENGTH} 字符)")

    return safe


def _validate_extension(filename: str) -> None:
    """校验扩展名白名单。"""
    # rfind 兼容文件名中含多个点的情况
    dot_idx = filename.rfind(".")
    if dot_idx < 0:
        raise UploadSecurityError("扩展名必须是 .md")
    ext = filename[dot_idx:].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadSecurityError(f"不允许的扩展名: {ext},仅支持 .md")


def _validate_content_type(content_type: str | None) -> None:
    """校验 MIME 类型。"""
    if not content_type:
        # 缺省时放行(部分客户端不发 content-type),后续靠扩展名 + 内容嗅探兜底
        return
    # 去掉 charset 等参数: text/markdown; charset=utf-8 → text/markdown
    ct = content_type.split(";")[0].strip().lower()
    if ct not in ALLOWED_CONTENT_TYPES:
        raise UploadSecurityError(f"不允许的 MIME 类型: {ct}")


def _validate_size(content: bytes) -> None:
    """校验文件大小。"""
    if len(content) > MAX_FILE_SIZE:
        raise UploadSecurityError(f"文件过大({len(content)} 字节 > {MAX_FILE_SIZE} 字节)")


def _validate_content(content: bytes) -> str:
    """内容嗅探 + UTF-8 解码,返回文本。"""
    # NUL 字节检测:防二进制伪装
    if b"\x00" in content:
        raise UploadSecurityError("文件含 NUL 字节,疑似二进制内容")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise UploadSecurityError(f"文件非 UTF-8 编码: {e}") from e

    return text


def validate_markdown_file(file: UploadFile) -> str:
    """完整校验上传的 Markdown 文件,返回解码后的文本。

    校验顺序:文件名 → 扩展名 → MIME → 大小 → 内容嗅探 → UTF-8。
    任一失败抛 UploadSecurityError。
    """
    safe_name = validate_filename(file.filename)
    _validate_extension(safe_name)
    _validate_content_type(file.content_type)

    content = file.file.read()
    _validate_size(content)
    text = _validate_content(content)

    return text
