"""测试 POST /admin/posts/upload:MD 文件上传解析 + 草稿创建。

使用 dependency_overrides mock 掉 DB 与鉴权,
避免依赖真实 PG 连接。

注意:admin 路由挂在 /api/admin 下,请求路径需带 /api 前缀。
"""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_admin_dep():
    """mock require_admin 依赖,返回 fake admin_id。"""
    from app.deps import require_admin
    from app.main import app

    async def _fake_admin():
        return "admin-test-id"

    app.dependency_overrides[require_admin] = _fake_admin
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_dep():
    """mock get_db 依赖,返回 MagicMock AsyncSession。"""
    from app.db.session import get_db
    from app.main import app

    async def _fake_db():
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.flush = AsyncMock()
        return session

    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


UPLOAD_URL = "/api/admin/posts/upload"


def _build_multipart(
    filename: str,
    content: bytes,
    channel_id: str = "00000000-0000-0000-0000-000000000001",
):
    """构造 multipart/form-data 请求体。"""
    files = {"file": (filename, io.BytesIO(content), "text/markdown")}
    data = {"channel_id": channel_id}
    return files, data


def _make_fake_post(**overrides):
    """构造一个 mock Post 对象,默认 status=draft。

    注意:MagicMock 的 name 是特殊参数(设置 mock 自身名而非属性),
    所以 channel 的 slug/name 必须用属性赋值方式设置。
    """
    fake = MagicMock()
    fake.id = "00000000-0000-0000-0000-000000000aaa"
    fake.slug = "test-slug"
    fake.title = "测试标题"
    fake.excerpt = None
    fake.content_md = "# 测试"
    fake.content_html = None
    fake.channel_id = "00000000-0000-0000-0000-000000000001"
    fake_channel = MagicMock()
    fake_channel.slug = "default"
    fake_channel.name = "默认"
    fake.channel = fake_channel
    fake.tags = None
    fake.status = "draft"
    fake.published_at = None
    fake.reading_time = None
    fake.toc = []
    fake.created_at = None
    fake.updated_at = None
    for k, v in overrides.items():
        setattr(fake, k, v)
    return fake


@pytest.mark.asyncio
async def test_upload_creates_draft(client, mock_admin_dep, mock_db_dep):
    """合法 md → 创建草稿 → 返回 ArticleAdmin。"""
    content = "# 我的第一篇文章\n\n正文内容。".encode("utf-8")
    files, data = _build_multipart("post.md", content)
    fake_post = _make_fake_post(
        slug="我的第一篇文章",
        title="我的第一篇文章",
        content_md="# 我的第一篇文章\n\n正文内容。",
    )

    with patch("app.api.admin.posts.post_crud") as mock_crud:
        mock_crud.get_by_slug = AsyncMock(return_value=None)
        mock_crud.create = AsyncMock(return_value=fake_post)
        mock_crud.get_with_channel = AsyncMock(return_value=fake_post)

        resp = await client.post(UPLOAD_URL, files=files, data=data)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    post_data = body["data"]
    assert post_data["status"] == "draft"
    assert post_data["title"] == "我的第一篇文章"
    assert post_data["slug"] == "我的第一篇文章"
    args, kwargs = mock_crud.create.call_args
    create_schema = args[1] if len(args) > 1 else kwargs.get("obj_in")
    assert create_schema.status == "draft"
    assert create_schema.title == "我的第一篇文章"
    assert "# 我的第一篇文章" in create_schema.content_md


@pytest.mark.asyncio
async def test_upload_uses_filename_when_no_h1(client, mock_admin_dep, mock_db_dep):
    """无 # 标题 → 用文件名(去 .md)作为 title。"""
    content = "纯文本,无标题".encode("utf-8")
    files, data = _build_multipart("note.md", content)
    fake_post = _make_fake_post(title="note", slug="note", content_md="纯文本,无标题")

    with patch("app.api.admin.posts.post_crud") as mock_crud:
        mock_crud.get_by_slug = AsyncMock(return_value=None)
        mock_crud.create = AsyncMock(return_value=fake_post)
        mock_crud.get_with_channel = AsyncMock(return_value=fake_post)

        resp = await client.post(UPLOAD_URL, files=files, data=data)

    assert resp.status_code == 200
    args, _ = mock_crud.create.call_args
    create_schema = args[1]
    assert create_schema.title == "note"


@pytest.mark.asyncio
async def test_upload_slug_conflict_auto_suffix(client, mock_admin_dep, mock_db_dep):
    """slug 冲突 → 自动加 -2 后缀。"""
    content = "# Test\n正文".encode("utf-8")
    files, data = _build_multipart("t.md", content)
    fake_post = _make_fake_post(title="Test", slug="test-2", content_md="# Test\n正文")

    with patch("app.api.admin.posts.post_crud") as mock_crud:
        # 第一次查 "test" 存在,第二次查 "test-2" 不存在
        mock_crud.get_by_slug = AsyncMock(side_effect=[MagicMock(), None])
        mock_crud.create = AsyncMock(return_value=fake_post)
        mock_crud.get_with_channel = AsyncMock(return_value=fake_post)

        resp = await client.post(UPLOAD_URL, files=files, data=data)

    assert resp.status_code == 200
    args, _ = mock_crud.create.call_args
    create_schema = args[1]
    assert create_schema.slug == "test-2"


@pytest.mark.asyncio
async def test_upload_rejects_bad_extension(client, mock_admin_dep, mock_db_dep):
    """非 .md 扩展名 → 400。"""
    files, data = _build_multipart("evil.exe", b"MZ")
    resp = await client.post(UPLOAD_URL, files=files, data=data)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] != 0
    assert "扩展名" in body["message"]


@pytest.mark.asyncio
async def test_upload_rejects_nul_byte(client, mock_admin_dep, mock_db_dep):
    """含 NUL 字节 → 400。"""
    files, data = _build_multipart("evil.md", b"# ok\x00binary")
    resp = await client.post(UPLOAD_URL, files=files, data=data)
    assert resp.status_code == 400
    body = resp.json()
    assert "NUL" in body["message"]


@pytest.mark.asyncio
async def test_upload_requires_admin(client):
    """无鉴权 → 401。"""
    files, data = _build_multipart("post.md", b"# ok")
    resp = await client.post(UPLOAD_URL, files=files, data=data)
    assert resp.status_code == 401
