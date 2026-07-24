"""文件上传安全验证。

策略(纵深防御,任一失败即拒绝):
1. 文件名:basename 化(防路径遍历)、长度限制、非空
2. 扩展名:白名单 .md(大小写不敏感)
3. MIME 类型:白名单 text/markdown | text/plain | text/x-markdown | application/octet-stream
4. 大小:上限 MAX_FILE_SIZE
5. 内容嗅探:拒绝 NUL 字节(防二进制伪装)
6. 编码:严格 UTF-8 解码

知识库多格式上传(validate_document_file)额外支持 txt/pdf/docx，按格式分级大小限制，
文本类(md/txt)做 NUL 嗅探 + 编码检测，二进制类(pdf/docx)做 magic bytes 校验。
"""
import re
from dataclasses import dataclass

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


# ===== 知识库多格式上传配置 =====

#: 各格式大小上限(字节)
MAX_SIZE_BY_FORMAT: dict[str, int] = {
    "md": 5 * 1024 * 1024,      # 5MB
    "txt": 5 * 1024 * 1024,     # 5MB
    "pdf": 20 * 1024 * 1024,    # 20MB
    "docx": 20 * 1024 * 1024,   # 20MB
}

#: 扩展名 → source_format 映射
EXT_TO_FORMAT: dict[str, str] = {
    ".md": "md",
    ".markdown": "md",
    ".txt": "txt",
    ".pdf": "pdf",
    ".docx": "docx",
}

#: 各格式允许的 MIME（application/octet-stream 作为浏览器兜底统一放行）
MIME_BY_FORMAT: dict[str, frozenset[str]] = {
    "md": frozenset({"text/markdown", "text/plain", "text/x-markdown", "application/octet-stream"}),
    "txt": frozenset({"text/plain", "application/octet-stream"}),
    "pdf": frozenset({"application/pdf", "application/octet-stream"}),
    "docx": frozenset({
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
        "application/zip",
    }),
}


class UploadSecurityError(Exception):
    """文件上传安全校验失败。"""


@dataclass
class ValidatedDocument:
    """多格式上传校验结果。

    - text: md/txt 为解码后的文本；pdf/docx 为 None（由 parser 从 raw 提取）
    - raw: 原始字节，所有格式均归档 MinIO
    """

    filename: str          # 安全 basename
    source_format: str     # md | txt | pdf | docx
    content_type: str      # 规范化后的 MIME（下载时还原 Content-Type）
    size: int
    raw: bytes
    text: str | None


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


# ===== 知识库多格式文档校验 =====


def _detect_source_format(filename: str) -> str:
    """从扩展名推断 source_format。"""
    dot_idx = filename.rfind(".")
    if dot_idx < 0:
        raise UploadSecurityError(f"文件无扩展名: {filename}")
    ext = filename[dot_idx:].lower()
    fmt = EXT_TO_FORMAT.get(ext)
    if not fmt:
        raise UploadSecurityError(
            f"不支持的扩展名: {ext},仅支持 .md/.txt/.pdf/.docx"
        )
    return fmt


def _validate_mime_for_format(content_type: str | None, source_format: str) -> str:
    """按格式校验 MIME，返回规范化后的 MIME。"""
    allowed = MIME_BY_FORMAT[source_format]
    if not content_type:
        # 未上报 MIME，用格式默认值
        return _default_mime(source_format)
    ct = content_type.split(";")[0].strip().lower()
    if ct not in allowed:
        raise UploadSecurityError(f"格式 {source_format} 不允许的 MIME: {ct}")
    # octet-stream 统一规范化为格式默认 MIME，便于下载时还原 Content-Type
    if ct == "application/octet-stream":
        return _default_mime(source_format)
    return ct


def _default_mime(source_format: str) -> str:
    return {
        "md": "text/markdown",
        "txt": "text/plain",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }[source_format]


def _decode_text_content(raw: bytes, source_format: str) -> str:
    """文本类(md/txt)解码：NUL 嗅探 + UTF-8 优先 + chardet 兜底。

    - md：要求严格 UTF-8（与文章渲染链一致，非 UTF-8 直接拒）
    - txt：UTF-8 失败时用 chardet 检测编码后解码（兼容历史 GBK 文本）
    """
    if b"\x00" in raw:
        raise UploadSecurityError("文件含 NUL 字节,疑似二进制内容")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        if source_format == "md":
            raise UploadSecurityError("Markdown 文件必须为 UTF-8 编码") from None
        # txt 兜底：chardet 检测
        import chardet

        detected = chardet.detect(raw)
        encoding = detected.get("encoding") or "utf-8"
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError) as e:
            raise UploadSecurityError(f"无法识别文本编码: {e}") from e


def _validate_pdf_magic(raw: bytes) -> None:
    """PDF magic bytes 校验：%PDF。"""
    if not raw.startswith(b"%PDF"):
        raise UploadSecurityError("PDF 文件头异常(缺少 %PDF 标识),疑似伪装文件")


def _validate_docx_magic(raw: bytes) -> None:
    """DOCX magic bytes 校验：PK Zip 头。

    docx 本质是 zip，前 2 字节为 PK(0x50 0x4b)。进一步校验需解压，
    此处仅做轻量头校验，深入校验交由 python-docx 解析时抛错。
    """
    if len(raw) < 4 or raw[:2] != b"PK":
        raise UploadSecurityError("DOCX 文件头异常(缺少 PK Zip 标识),疑似伪装文件")


def validate_document_file(file: UploadFile) -> ValidatedDocument:
    """校验知识库多格式上传文件(md/txt/pdf/docx)。

    校验顺序：文件名 → 扩展名(定 source_format) → MIME → 大小(按格式分级)
              → 内容校验(md/txt 解码为 text；pdf/docx magic bytes)。

    返回 ValidatedDocument，含 raw(归档 MinIO) + text(md/txt 解码文本，pdf/docx 为 None)。
    任一失败抛 UploadSecurityError。
    """
    safe_name = validate_filename(file.filename)
    source_format = _detect_source_format(safe_name)
    content_type = _validate_mime_for_format(file.content_type, source_format)

    raw = file.file.read()
    size = len(raw)
    max_size = MAX_SIZE_BY_FORMAT[source_format]
    if size > max_size:
        raise UploadSecurityError(
            f"文件过大({size} 字节 > {max_size} 字节,格式 {source_format} 上限 "
            f"{max_size // 1024 // 1024}MB)"
        )

    text: str | None = None
    if source_format in ("md", "txt"):
        text = _decode_text_content(raw, source_format)
    elif source_format == "pdf":
        _validate_pdf_magic(raw)
    elif source_format == "docx":
        _validate_docx_magic(raw)

    return ValidatedDocument(
        filename=safe_name,
        source_format=source_format,
        content_type=content_type,
        size=size,
        raw=raw,
        text=text,
    )
