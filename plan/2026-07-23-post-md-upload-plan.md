# 文章 Markdown 文件上传 实现计划

> **For Codex:** 按 superpowers:executing-plans 任务逐条执行。

**目标:** 在后台文章管理中增加 `.md` 文件上传入口,后端安全验证 + 解析后创建草稿,前端跳转到编辑页继续编辑。

**架构:**
- 后端:在 `admin/posts.py` 新增 `POST /admin/posts/upload`(multipart),复用 `AdminId` 鉴权与现有 `post_crud.create`。
- 解析:首个 `# 一级标题` → `title`,文件名兜底;`slug` 由 `utils/slug.py` 生成;冲突自动加 `-2`/`-3` 后缀。
- 安全:独立 `services/upload_security.py` 模块,统一扩展名/MIME/大小/NUL 字节/UTF-8/文件名安全校验。
- RAG:本次不实现,沿用现有 `_try_dispatch_ingest_publish`(发布时才触发,草稿状态不调用)。
- 前端:文章列表页新增"上传 MD"按钮 → 选频道 Modal → 上传成功后跳 `/admin/posts/{id}/edit`。

**技术栈:** FastAPI + python-multipart + Pydantic v2 / Next.js 14 + Ant Design + React Query + axios。

---

## 任务清单概览

| # | 任务 | 类型 | 依赖 |
|---|------|------|------|
| 1 | 实现 `utils/slug.py` slugify 函数 | 后端纯函数 | 无 |
| 2 | 实现 `services/upload_security.py` 文件安全验证 | 后端纯函数 | 无 |
| 3 | 实现 `ingest/toc.py` TOC 生成辅助 | 后端纯函数 | 无 |
| 4 | 实现 `POST /admin/posts/upload` 路由 + 集成测试 | 后端 API | 1, 2, 3 |
| 5 | 前端 API 封装 `postsApi.uploadMd` | 前端 | 4 契约 |
| 6 | 前端 React Query hook `useUploadPostMd` | 前端 | 5 |
| 7 | 前端文章列表页上传 Modal UI | 前端 | 6 |

---

## Task 1: 实现 slugify 函数

**Files:**
- Modify: `backend/app/utils/slug.py`(当前只有一行 docstring)
- Test: `backend/tests/test_slug.py`(新建)

### Step 1: 写失败测试

写入 `backend/tests/test_slug.py`:

```python
"""测试 utils/slug.py:slug 生成。"""
from app.utils.slug import slugify


def test_slugify_ascii():
    """纯 ASCII:转小写、空格转连字符。"""
    assert slugify("Hello World") == "hello-world"


def test_slugify_chinese():
    """中文:转拼音首字母(简单实现:保留非 ASCII 字符原样)。

    P0 简化:不做完整拼音转换,中文标题保留中文字符。
    通过 slug 冲突时自动加后缀保证唯一性。
    """
    # 简化策略:非 ASCII 字符原样保留,空格转连字符,小写化
    assert slugify("我的第一篇文章") == "我的第一篇文章"


def test_slugify_mixed():
    """中英混合。"""
    assert slugify("React 入门 Guide") == "react-入门-guide"


def test_slugify_special_chars():
    """特殊字符:替换为连字符,合并连续连字符。"""
    assert slugify("Hello!!! World???") == "hello-world"


def test_slugify_leading_trailing_hyphens():
    """首尾连字符去除。"""
    assert slugify("---hello---") == "hello"


def test_slugify_empty():
    """空字符串返回空。"""
    assert slugify("") == ""


def test_slugify_max_length():
    """超过 120 字符截断(Post.slug 限制 120)。"""
    long_title = "a" * 200
    result = slugify(long_title)
    assert len(result) <= 120
    assert result == "a" * 120


def test_slugify_preserves_digits():
    """数字保留。"""
    assert slugify("Post 2024 v2") == "post-2024-v2"
```

### Step 2: 运行测试确认失败

Run: `cd backend && python -m pytest tests/test_slug.py -v`
Expected: FAIL with `ImportError: cannot import name 'slugify'`

### Step 3: 实现 slugify

替换 `backend/app/utils/slug.py` 全部内容:

```python
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
    2. 非 [a-z0-9\u4e00-\u9fff] 字符替换为连字符
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
```

### Step 4: 运行测试确认通过

Run: `cd backend && python -m pytest tests/test_slug.py -v`
Expected: 8 passed

### Step 5: 提交

```bash
cd backend
git add app/utils/slug.py tests/test_slug.py
git commit -m "feat(slug): 实现 slugify 函数支持中英文混合标题"
```

---

## Task 2: 实现文件安全验证模块

**Files:**
- Create: `backend/app/services/upload_security.py`
- Test: `backend/tests/services/test_upload_security.py`(新建,需建 `__init__.py`)

### Step 1: 写失败测试

写入 `backend/tests/services/__init__.py`(空文件)。

写入 `backend/tests/services/test_upload_security.py`:

```python
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
    """构造 Starlette UploadFile 替身(测试用)。"""
    from starlette.datastructures import UploadFile

    return UploadFile(filename=filename, file=io.BytesIO(content), content_type=content_type)


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
```

### Step 2: 运行测试确认失败

Run: `cd backend && python -m pytest tests/services/test_upload_security.py -v`
Expected: FAIL with `ImportError`

### Step 3: 实现 upload_security

写入 `backend/app/services/upload_security.py`:

```python
"""文件上传安全验证。

策略(纵深防御,任一失败即拒绝):
1. 文件名:basename 化(防路径遍历)、长度限制、非空
2. 扩展名:白名单 .md(大小写不敏感)
3. MIME 类型:白名单 text/markdown | text/plain | text/x-markdown | application/octet-stream
4. 大小:上限 MAX_FILE_SIZE
5. 内容嗅探:拒绝 NUL 字节(防二进制伪装)
6. 编码:严格 UTF-8 解码
"""
import os
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
        raise UploadSecurityError(
            f"文件名过长(>{MAX_FILENAME_LENGTH} 字符)"
        )

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
        raise UploadSecurityError(
            f"文件过大({len(content)} 字节 > {MAX_FILE_SIZE} 字节)"
        )


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
```

### Step 4: 运行测试确认通过

Run: `cd backend && python -m pytest tests/services/test_upload_security.py -v`
Expected: 16 passed

### Step 5: 提交

```bash
cd backend
git add app/services/upload_security.py tests/services/__init__.py tests/services/test_upload_security.py
git commit -m "feat(upload): 实现文件上传安全验证模块"
```

---

## Task 3: 实现 TOC 生成辅助

**Files:**
- Create: `backend/app/ingest/toc.py`
- Test: `backend/tests/ingest/test_toc.py`(需建 `__init__.py`,可能已存在)

### Step 1: 检查现有 ingest 测试目录

Run: `cd backend && ls tests/ingest/`
Expected: 看到 `__init__.py` 已存在。

### Step 2: 写失败测试

写入 `backend/tests/ingest/test_toc.py`:

```python
"""测试 ingest/toc.py:从 ParsedDoc.headings 生成 TocItem 列表。"""
from app.ingest.parser import parse_markdown
from app.ingest.toc import headings_to_toc


def test_toc_empty():
    """无标题 → 空 toc。"""
    parsed = parse_markdown("T", "纯文本")
    assert headings_to_toc(parsed.headings) == []


def test_toc_basic():
    """基本标题层级转 TocItem。"""
    content = "# 一级\n## 二级\n### 三级"
    parsed = parse_markdown("T", content)
    toc = headings_to_toc(parsed.headings)
    assert len(toc) == 3
    assert toc[0] == {"id": "一级", "title": "一级", "level": 1}
    assert toc[1] == {"id": "二级", "title": "二级", "level": 2}
    assert toc[2] == {"id": "三级", "title": "三级", "level": 3}


def test_toc_dedup_ids():
    """重复标题:第二个 id 加 -2 后缀。"""
    content = "# 标题\n# 标题\n# 标题"
    parsed = parse_markdown("T", content)
    toc = headings_to_toc(parsed.headings)
    ids = [item["id"] for item in toc]
    assert ids == ["标题", "标题-2", "标题-3"]


def test_toc_preserves_text():
    """title 保留原文(含空格/标点)。"""
    content = "# Hello, World!"
    parsed = parse_markdown("T", content)
    toc = headings_to_toc(parsed.headings)
    assert toc[0]["title"] == "Hello, World!"
    assert toc[0]["id"] == "hello-world"
```

### Step 3: 运行测试确认失败

Run: `cd backend && python -m pytest tests/ingest/test_toc.py -v`
Expected: FAIL with `ImportError: cannot import name 'headings_to_toc'`

### Step 4: 实现 toc 辅助

写入 `backend/app/ingest/toc.py`:

```python
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
```

### Step 5: 运行测试确认通过

Run: `cd backend && python -m pytest tests/ingest/test_toc.py -v`
Expected: 4 passed

### Step 6: 提交

```bash
cd backend
git add app/ingest/toc.py tests/ingest/test_toc.py
git commit -m "feat(toc): 实现从 headings 生成 TocItem 辅助函数"
```

---

## Task 4: 实现 `POST /admin/posts/upload` 路由

**Files:**
- Modify: `backend/app/api/admin/posts.py`(新增 upload 端点 + 辅助函数)
- Test: `backend/tests/api/test_upload_post.py`(新建,需建 `__init__.py` 已存在)

### Step 1: 写失败测试

写入 `backend/tests/api/test_upload_post.py`:

```python
"""测试 POST /admin/posts/upload:MD 文件上传解析 + 草稿创建。

使用 dependency_overrides mock 掉 DB 与鉴权,
避免依赖真实 PG 连接。
"""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_admin_dep(client):
    """mock require_admin 依赖,返回 fake admin_id。"""
    from app.deps import require_admin

    async def _fake_admin():
        return "admin-test-id"

    client.app.dependency_overrides[require_admin] = _fake_admin
    yield
    client.app.dependency_overrides.clear()


@pytest.fixture
def mock_db_dep(client):
    """mock get_db 依赖,返回 MagicMock AsyncSession。"""
    from app.db.session import get_db

    async def _fake_db():
        session = AsyncMock()
        # commit / refresh 等无返回值
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.flush = AsyncMock()
        return session

    client.app.dependency_overrides[get_db] = _fake_db
    yield
    client.app.dependency_overrides.clear()


def _build_multipart(filename: str, content: bytes, channel_id: str = "00000000-0000-0000-0000-000000000001"):
    """构造 multipart/form-data 请求体。"""
    files = {"file": (filename, io.BytesIO(content), "text/markdown")}
    data = {"channel_id": channel_id}
    return files, data


@pytest.mark.asyncio
async def test_upload_creates_draft(client, mock_admin_dep, mock_db_dep):
    """合法 md → 创建草稿 → 返回 ArticleAdmin。"""
    content = "# 我的第一篇文章\n\n正文内容。".encode("utf-8")
    files, data = _build_multipart("post.md", content)

    # mock post_crud:slug 不存在 → 创建 → 返回带 channel 的 post
    fake_post = MagicMock()
    fake_post.id = "00000000-0000-0000-0000-000000000aaa"
    fake_post.slug = "我的第一篇文章"
    fake_post.title = "我的第一篇文章"
    fake_post.excerpt = None
    fake_post.content_md = "# 我的第一篇文章\n\n正文内容。"
    fake_post.content_html = None
    fake_post.channel_id = "00000000-0000-0000-0000-000000000001"
    fake_post.channel = MagicMock(slug="default", name="默认")
    fake_post.tags = None
    fake_post.status = "draft"
    fake_post.published_at = None
    fake_post.reading_time = None
    fake_post.toc = []
    fake_post.created_at = None
    fake_post.updated_at = None

    with patch("app.api.admin.posts.post_crud") as mock_crud:
        mock_crud.get_by_slug = AsyncMock(return_value=None)  # slug 不存在
        mock_crud.create = AsyncMock(return_value=fake_post)
        mock_crud.get_with_channel = AsyncMock(return_value=fake_post)

        resp = await client.post("/admin/posts/upload", files=files, data=data)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    post_data = body["data"]
    assert post_data["status"] == "draft"
    assert post_data["title"] == "我的第一篇文章"
    assert post_data["slug"] == "我的第一篇文章"
    # create 收到的 PostCreate 应有正确字段
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

    fake_post = MagicMock()
    fake_post.id = "post-1"
    fake_post.title = "note"
    fake_post.slug = "note"
    fake_post.status = "draft"
    fake_post.toc = []
    fake_post.tags = None
    fake_post.excerpt = None
    fake_post.content_md = "纯文本,无标题"
    fake_post.content_html = None
    fake_post.channel_id = "00000000-0000-0000-0000-000000000001"
    fake_post.channel = MagicMock(slug="default", name="默认")
    fake_post.published_at = None
    fake_post.reading_time = None
    fake_post.created_at = None
    fake_post.updated_at = None

    with patch("app.api.admin.posts.post_crud") as mock_crud:
        mock_crud.get_by_slug = AsyncMock(return_value=None)
        mock_crud.create = AsyncMock(return_value=fake_post)
        mock_crud.get_with_channel = AsyncMock(return_value=fake_post)

        resp = await client.post("/admin/posts/upload", files=files, data=data)

    assert resp.status_code == 200
    args, _ = mock_crud.create.call_args
    create_schema = args[1]
    assert create_schema.title == "note"


@pytest.mark.asyncio
async def test_upload_slug_conflict_auto_suffix(client, mock_admin_dep, mock_db_dep):
    """slug 冲突 → 自动加 -2 后缀。"""
    content = "# Test\n正文".encode("utf-8")
    files, data = _build_multipart("t.md", content)

    existing = MagicMock()  # 已存在的同 slug 文章
    fake_post = MagicMock()
    fake_post.id = "new-id"
    fake_post.title = "Test"
    fake_post.slug = "test-2"
    fake_post.status = "draft"
    fake_post.toc = []
    fake_post.tags = None
    fake_post.excerpt = None
    fake_post.content_md = "# Test\n正文"
    fake_post.content_html = None
    fake_post.channel_id = "00000000-0000-0000-0000-000000000001"
    fake_post.channel = MagicMock(slug="default", name="默认")
    fake_post.published_at = None
    fake_post.reading_time = None
    fake_post.created_at = None
    fake_post.updated_at = None

    with patch("app.api.admin.posts.post_crud") as mock_crud:
        # 第一次查 "test" 存在,第二次查 "test-2" 不存在
        mock_crud.get_by_slug = AsyncMock(side_effect=[existing, None])
        mock_crud.create = AsyncMock(return_value=fake_post)
        mock_crud.get_with_channel = AsyncMock(return_value=fake_post)

        resp = await client.post("/admin/posts/upload", files=files, data=data)

    assert resp.status_code == 200
    args, _ = mock_crud.create.call_args
    create_schema = args[1]
    assert create_schema.slug == "test-2"


@pytest.mark.asyncio
async def test_upload_rejects_bad_extension(client, mock_admin_dep, mock_db_dep):
    """非 .md 扩展名 → 400。"""
    files, data = _build_multipart("evil.exe", b"MZ")
    resp = await client.post("/admin/posts/upload", files=files, data=data)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] != 0
    assert "扩展名" in body["message"]


@pytest.mark.asyncio
async def test_upload_rejects_nul_byte(client, mock_admin_dep, mock_db_dep):
    """含 NUL 字节 → 400。"""
    files, data = _build_multipart("evil.md", b"# ok\x00binary")
    resp = await client.post("/admin/posts/upload", files=files, data=data)
    assert resp.status_code == 400
    body = resp.json()
    assert "NUL" in body["message"]


@pytest.mark.asyncio
async def test_upload_requires_admin(client):
    """无鉴权 → 401。"""
    files, data = _build_multipart("post.md", b"# ok")
    resp = await client.post("/admin/posts/upload", files=files, data=data)
    assert resp.status_code == 401
```

### Step 2: 运行测试确认失败

Run: `cd backend && python -m pytest tests/api/test_upload_post.py -v`
Expected: FAIL with `404 Not Found`(路由未定义)

### Step 3: 实现 upload 路由

在 `backend/app/api/admin/posts.py` 顶部 import 区追加:

```python
from fastapi import File, Form, UploadFile

from app.ingest.parser import parse_markdown
from app.ingest.toc import headings_to_toc
from app.services.upload_security import (
    UploadSecurityError,
    validate_markdown_file,
)
from app.utils.slug import slugify
```

在 `backend/app/api/admin/posts.py` 文件末尾(在 `revalidate` 路由之后)追加新路由 + 辅助函数:

```python
def _extract_title_and_slug(content_md: str, filename: str) -> tuple[str, str]:
    """从 Markdown 内容提取标题与 slug。

    - title:首个 # 一级标题;无则用文件名(去 .md)
    - slug:title 经 slugify 生成
    """
    import re

    # 找首个一级标题
    for line in content_md.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            title = m.group(1).strip()
            return title, slugify(title)

    # 兜底:文件名去 .md
    base = filename
    if base.lower().endswith(".md"):
        base = base[:-3]
    title = base.strip() or "untitled"
    return title, slugify(title) or "untitled"


async def _ensure_unique_slug(
    db: AsyncSession,
    base_slug: str,
) -> str:
    """slug 冲突时自动加 -2/-3 后缀直到唯一。"""
    from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F811

    candidate = base_slug
    suffix = 2
    while await post_crud.get_by_slug(db, candidate):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate


@router.post("/upload")
async def upload_post_md(
    db: DBSession,
    _: AdminId,
    file: UploadFile = File(...),
    channel_id: UUID = Form(...),
) -> dict:
    """上传 Markdown 文件 → 解析 → 创建草稿 → 返回 ArticleAdmin。

    流程:
    1. 安全验证(扩展名/MIME/大小/NUL/UTF-8)
    2. 提取 title 与 slug(首 # 标题优先,文件名兜底)
    3. slug 冲突时自动加 -2/-3 后缀
    4. 解析 headings 生成 toc
    5. 创建 status=draft 文章(不触发 RAG 入库)
    6. 返回 ArticleAdmin,前端跳 /admin/posts/{id}/edit

    RAG 入库在文章发布时由 update_status 触发,本接口不调用。
    """
    # 1. 安全验证
    try:
        content_md = validate_markdown_file(file)
    except UploadSecurityError as e:
        raise AppError(str(e), status_code=400, code=4000) from e

    # 2. 提取 title 与 slug
    title, base_slug = _extract_title_and_slug(content_md, file.filename or "untitled.md")

    # 3. slug 唯一化
    slug = await _ensure_unique_slug(db, base_slug)

    # 4. 生成 toc
    parsed = parse_markdown(title=title, content_md=content_md, slug=slug)
    toc = headings_to_toc(parsed.headings)

    # 5. 创建草稿
    payload = PostCreate(
        slug=slug,
        title=title,
        content_md=content_md,
        channel_id=channel_id,
        status="draft",
        toc=toc,
    )
    p = await post_crud.create(db, payload)
    await db.commit()
    p = await post_crud.get_with_channel(db, p.id)
    logger.info("post_uploaded", post_id=str(p.id), slug=p.slug, filename=file.filename)
    return envelope(_to_admin(p).model_dump())
```

**注意:** 顶部还需要追加 `from app.core.errors import AppError` 与 `from sqlalchemy.ext.asyncio import AsyncSession`。检查现有 imports,`AppError` 未引入,需要追加。

修订后的顶部 import 块(替换原 import 块)应在 Step 3 实施时一并完成:

```python
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.crud.post import post as post_crud
from app.deps import AdminId, DBSession
from app.ingest.parser import parse_markdown
from app.ingest.toc import headings_to_toc
from app.schemas.common import Page, envelope
from app.schemas.post import (
    ArticleAdmin,
    PostCreate,
    PostStatusUpdate,
    PostUpdate,
)
from app.services.upload_security import (
    UploadSecurityError,
    validate_markdown_file,
)
from app.utils.slug import slugify
```

`_ensure_unique_slug` 内的 `from sqlalchemy.ext.asyncio import AsyncSession` 是冗余(顶部已引入),删除该行。

最终 `_ensure_unique_slug` 简化为:

```python
async def _ensure_unique_slug(db: AsyncSession, base_slug: str) -> str:
    """slug 冲突时自动加 -2/-3 后缀直到唯一。"""
    candidate = base_slug
    suffix = 2
    while await post_crud.get_by_slug(db, candidate):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate
```

### Step 4: 运行测试确认通过

Run: `cd backend && python -m pytest tests/api/test_upload_post.py -v`
Expected: 6 passed

### Step 5: 运行全量测试确认无回归

Run: `cd backend && python -m pytest -v`
Expected: 全部通过(含原有 test_health / test_parser / test_security 等)

### Step 6: 提交

```bash
cd backend
git add app/api/admin/posts.py tests/api/test_upload_post.py
git commit -m "feat(posts): 新增 POST /admin/posts/upload MD 文件上传接口"
```

---

## Task 5: 前端 API 封装 `postsApi.uploadMd`

**Files:**
- Modify: `web/lib/api/admin.ts`

### Step 1: 在 `postsApi` 对象内追加 uploadMd 方法

在 `web/lib/api/admin.ts` 的 `postsApi` 对象内(在 `setStatus` 之后)追加:

```typescript
  uploadMd(file: File, channelId: string) {
    const form = new FormData();
    form.append('file', file);
    form.append('channel_id', channelId);
    // axios 自动设置 multipart/form-data boundary,不要手动设 Content-Type
    return unwrap<AdminPost>(
      request.post('/admin/posts/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000, // 文件上传放宽超时
      }),
    );
  },
```

注:`unwrap` 与 `request` 已在文件顶部引入;`AdminPost` 已定义。

### Step 2: 类型检查

Run: `cd web && npx tsc --noEmit`
Expected: 无错误

### Step 3: 提交

```bash
cd web
git add lib/api/admin.ts
git commit -m "feat(api): 新增 postsApi.uploadMd 前端封装"
```

---

## Task 6: 前端 React Query hook `useUploadPostMd`

**Files:**
- Modify: `web/hooks/useAdmin.ts`

### Step 1: 在 Posts 区块追加 hook

在 `web/hooks/useAdmin.ts` 的 `useSetPostStatus` 之后追加:

```typescript
export function useUploadPostMd(
  opts?: UseMutationOptions<AdminPost, Error, { file: File; channelId: string }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, channelId }) => postsApi.uploadMd(file, channelId),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}
```

### Step 2: 类型检查

Run: `cd web && npx tsc --noEmit`
Expected: 无错误

### Step 3: 提交

```bash
cd web
git add hooks/useAdmin.ts
git commit -m "feat(hooks): 新增 useUploadPostMd mutation hook"
```

---

## Task 7: 前端文章列表页上传 Modal UI

**Files:**
- Modify: `web/app/admin/posts/page.tsx`

### Step 1: 在文章列表页顶部 import 区追加

```typescript
import { App, Button, Input, Modal, Select, Space, Table, Tag, Tooltip, Upload } from 'antd';
import type { UploadProps } from 'antd';
import { Edit3, Plus, Trash2, Send, Archive, FileEdit, Upload as UploadIcon } from 'lucide-react';
import { useAdminChannels, useAdminPosts, useDeletePost, useSetPostStatus, useUploadPostMd } from '@/hooks/useAdmin';
```

(原 `import { App, Button, Input, Select, Space, Table, Tag, Tooltip } from 'antd';` 替换为含 Modal/Upload 的版本;`lucide-react` 增加 Upload 图标;`useAdmin` 增加 `useUploadPostMd`。)

### Step 2: 在 `AdminPostsPage` 组件内增加上传状态与 Modal

在 `const [size, setSize] = useState(20);` 之后追加:

```typescript
  // 上传 MD 文件
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadChannelId, setUploadChannelId] = useState<string>('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const uploadPostMd = useUploadPostMd({
    onSuccess: (data) => {
      message.success('已导入,跳转编辑页');
      setUploadOpen(false);
      setUploadFile(null);
      setUploadChannelId('');
      router.push(`/admin/posts/${data.id}/edit`);
    },
    onError: (e) => message.error(e.message),
  });
```

(注:需要在组件顶部 `const router = useRouter();` 引入,见 Step 3。)

### Step 3: 引入 useRouter

在组件顶部 `const { message, modal } = App.useApp();` 之后追加:

```typescript
  const router = useRouter();
```

并在文件顶部 import 区追加:

```typescript
import { useRouter } from 'next/navigation';
```

### Step 4: 增加 antd Upload 配置与 Modal 渲染

在 `return (` 的根 `<div>` 内,顶部按钮区(原"新建文章"按钮旁)增加"上传 MD"按钮:

```tsx
        <Space>
          <Button icon={<UploadIcon size={14} />} onClick={() => setUploadOpen(true)}>
            上传 MD
          </Button>
          <Link href="/admin/posts/new">
            <Button type="primary" icon={<Plus size={14} />}>
              新建文章
            </Button>
          </Link>
        </Space>
```

(替换原单个 `<Link href="/admin/posts/new">...` 块。)

在 `<Table>` 之后(组件根 `<div>` 末尾,`</div>` 之前)追加上传 Modal:

```tsx
      {/* 上传 MD Modal */}
      <Modal
        title="上传 Markdown 文件"
        open={uploadOpen}
        onCancel={() => {
          setUploadOpen(false);
          setUploadFile(null);
          setUploadChannelId('');
        }}
        onOk={() => {
          if (!uploadFile) {
            message.warning('请选择 .md 文件');
            return;
          }
          if (!uploadChannelId) {
            message.warning('请选择频道');
            return;
          }
          uploadPostMd.mutate({ file: uploadFile, channelId: uploadChannelId });
        }}
        okText="解析并创建草稿"
        cancelText="取消"
        confirmLoading={uploadPostMd.isPending}
        okButtonProps={{ disabled: !uploadFile || !uploadChannelId }}
      >
        <div className="space-y-4 py-2">
          <div>
            <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-2">
              频道
            </div>
            <Select
              value={uploadChannelId || undefined}
              onChange={setUploadChannelId}
              placeholder="选择频道"
              style={{ width: '100%' }}
              options={(channelsData?.items || []).map((c) => ({
                label: c.name,
                value: c.id,
              }))}
            />
          </div>
          <div>
            <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-2">
              Markdown 文件
            </div>
            <Upload
              accept=".md,.markdown"
              maxCount={1}
              beforeUpload={(file) => {
                setUploadFile(file);
                return false; // 阻止自动上传,由 Modal onOk 触发
              }}
              onRemove={() => setUploadFile(null)}
              fileList={
                uploadFile
                  ? [
                      {
                        uid: '-1',
                        name: uploadFile.name,
                        status: 'done',
                      },
                    ]
                  : []
              }
            >
              <Button icon={<UploadIcon size={14} />}>选择 .md 文件</Button>
            </Upload>
            <div className="font-mono text-label-mono text-tertiary-fixed mt-2">
              仅支持 .md / .markdown,≤ 5MB,UTF-8 编码
            </div>
          </div>
        </div>
      </Modal>
```

### Step 5: 类型检查

Run: `cd web && npx tsc --noEmit`
Expected: 无错误

### Step 6: 手动验证

Run: `cd web && npm run dev`(若未起)

打开浏览器访问 `http://localhost:3000/admin/posts`:
1. 点击"上传 MD"按钮 → Modal 弹出
2. 选频道 + 选 .md 文件 → 点"解析并创建草稿"
3. 成功后跳转 `/admin/posts/{id}/edit`,表单预填 title/slug/content_md
4. 测试错误场景:上传 .txt → 报错提示"扩展名";上传含 NUL 字节文件 → 报错"NUL"

### Step 7: 提交

```bash
cd web
git add app/admin/posts/page.tsx
git commit -m "feat(posts): 文章列表页新增上传 MD 文件 Modal"
```

---

## 完成验收清单

- [ ] `POST /admin/posts/upload` 接受 multipart(file + channel_id)
- [ ] 安全验证:扩展名/MIME/大小/NUL/UTF-8/文件名 全部覆盖
- [ ] 解析:首 `#` 标题优先,文件名兜底
- [ ] slug 冲突自动加 `-2`/`-3` 后缀
- [ ] 创建 status=draft 草稿,不触发 RAG
- [ ] 前端列表页"上传 MD"按钮 → Modal → 跳编辑页
- [ ] 单元测试覆盖:slugify / upload_security / toc / upload 路由
- [ ] 全量 `pytest` 与 `tsc --noEmit` 通过

## 范围外(后续任务)

- 知识库 `POST /api/knowledge/upload` 通用文档上传(PDF/DOCX)
- Bytemd 编辑器接入替换 textarea
- RAG 入库管道(Celery 任务体实现)
- 发布时自动 revalidate Next.js SSG
