"""测试 services/upload_security.py:文件上传安全验证。"""
import io

import pytest

from app.services.upload_security import (
    MAX_FILE_SIZE,
    UploadSecurityError,
    validate_filename,
    validate_markdown_file,
)


def _make_upload_file(
    filename: str,
    content: bytes,
    content_type: str = "text/markdown",
):
    """构造 Starlette UploadFile 替身(测试用)。

    Starlette 1.x 移除了 content_type 参数,改用 headers 传递 Content-Type,
    UploadFile.content_type 属性会从 headers 解析。
    """
    from starlette.datastructures import Headers, UploadFile

    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_validate_markdown_file_basic():
    """合法 md 文件通过。"""
    content = "# 标题\n正文".encode("utf-8")
    f = _make_upload_file("post.md", content)
    text = validate_markdown_file(f)
    assert text == "# 标题\n正文"


def test_validate_markdown_file_extension_case_insensitive():
    """扩展名大小写不敏感。"""
    f = _make_upload_file("POST.MD", b"# ok")
    assert validate_markdown_file(f) == "# ok"


def test_validate_markdown_file_reject_txt():
    """拒绝 .txt 扩展名。"""
    f = _make_upload_file("post.txt", b"# ok")
    with pytest.raises(UploadSecurityError, match="扩展名"):
        validate_markdown_file(f)


def test_validate_markdown_file_reject_no_extension():
    """拒绝无扩展名。"""
    f = _make_upload_file("post", b"# ok")
    with pytest.raises(UploadSecurityError, match="扩展名"):
        validate_markdown_file(f)


def test_validate_markdown_file_reject_bad_mime():
    """拒绝非文本 MIME。"""
    f = _make_upload_file("a.md", b"# ok", content_type="application/x-msdownload")
    with pytest.raises(UploadSecurityError, match="MIME"):
        validate_markdown_file(f)


def test_validate_markdown_file_allows_octet_stream():
    """application/octet-stream 兜底通过(部分浏览器不识别 md MIME)。"""
    f = _make_upload_file("a.md", b"# ok", content_type="application/octet-stream")
    assert validate_markdown_file(f) == "# ok"


def test_validate_markdown_file_reject_oversize():
    """超过大小上限拒绝。"""
    big = b"a" * (MAX_FILE_SIZE + 1)
    f = _make_upload_file("big.md", big)
    with pytest.raises(UploadSecurityError, match="过大"):
        validate_markdown_file(f)


def test_validate_markdown_file_reject_nul_byte():
    """含 NUL 字节拒绝(防二进制伪装)。"""
    f = _make_upload_file("evil.md", b"# ok\x00binary")
    with pytest.raises(UploadSecurityError, match="NUL"):
        validate_markdown_file(f)


def test_validate_markdown_file_reject_invalid_utf8():
    """非 UTF-8 内容拒绝。"""
    f = _make_upload_file("gbk.md", b"# \xc4\xe3\xba\xc3")  # GBK "你好"
    with pytest.raises(UploadSecurityError, match="UTF-8"):
        validate_markdown_file(f)


def test_validate_filename_basic():
    """合法文件名通过。"""
    assert validate_filename("post.md") == "post.md"


def test_validate_filename_strips_path():
    """去除路径分隔符,只保留 basename。"""
    assert validate_filename("../../etc/passwd.md") == "passwd.md"
    assert validate_filename("a/b/c.md") == "c.md"
    # Windows 路径
    assert validate_filename("C:\\Users\\x\\post.md") == "post.md"


def test_validate_filename_rejects_empty():
    """空文件名拒绝。"""
    with pytest.raises(UploadSecurityError, match="文件名"):
        validate_filename("")


def test_validate_filename_rejects_too_long():
    """超长文件名拒绝。"""
    long_name = "a" * 300 + ".md"
    with pytest.raises(UploadSecurityError, match="过长"):
        validate_filename(long_name)


def test_validate_filename_rejects_empty_after_basename():
    """basename 后为空(如 "../../")拒绝。"""
    with pytest.raises(UploadSecurityError, match="文件名"):
        validate_filename("../../")


def test_max_file_size_constant():
    """大小上限常量 = 5MB。"""
    assert MAX_FILE_SIZE == 5 * 1024 * 1024
