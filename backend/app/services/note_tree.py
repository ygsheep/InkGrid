"""知识库目录树聚合。

按 category + folder_path 统计笔记数，组装成树结构返回。
- 7 个固定 category 节点（label/code 是固定元信息）
- 每个 category 下按 folder_path 聚合子文件夹（扁平列表，key 为完整路径）
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note_template import NoteTemplate
from app.models.post import Post
from app.schemas.note import NoteTreeFolder, NoteTreeNode

# 7 层目录固定元信息：(category_key, label, code)
CATEGORY_META: list[tuple[str, str, str]] = [
    ("inbox", "收集箱", "00_Inbox"),
    ("daily", "每日笔记", "01_Daily"),
    ("reading", "阅读笔记", "02_Reading"),
    ("knowledge", "主题知识", "03_Knowledge"),
    ("projects", "项目资料", "04_Projects"),
    ("templates", "模板库", "05_Templates"),
    ("assets", "资源库", "06_Assets"),
]


async def build_tree(db: AsyncSession) -> list[NoteTreeNode]:
    """构建目录树。

    - posts 表：按 category + folder_path 分组计数
    - note_templates 表：templates category 单独计数
    - assets：K2 暂不统计（返回 0）
    """
    # posts 按 category + folder_path 聚合
    stmt = (
        select(
            Post.category,
            Post.folder_path,
            func.count(Post.id).label("cnt"),
        )
        .group_by(Post.category, Post.folder_path)
    )
    rows = (await db.execute(stmt)).all()

    # 组织成 {category: {folder_path_or_None: count}}
    cat_total: dict[str, int] = {}
    folder_counts: dict[str, dict[str | None, int]] = {}
    for row in rows:
        cat = row.category
        fp = row.folder_path
        cnt = row.cnt
        cat_total[cat] = cat_total.get(cat, 0) + cnt
        folder_counts.setdefault(cat, {})
        folder_counts[cat][fp] = cnt

    # templates 计数
    tpl_cnt = (
        await db.execute(select(func.count(NoteTemplate.id)))
    ).scalar_one()
    cat_total["templates"] = int(tpl_cnt or 0)

    # 组装树
    nodes: list[NoteTreeNode] = []
    for key, label, code in CATEGORY_META:
        children: list[NoteTreeFolder] = []
        cat_folders = folder_counts.get(key, {})
        # folder_path 非空的子目录
        for fp, cnt in sorted(
            (fp, c) for fp, c in cat_folders.items() if fp
        ):
            # label 取最后一段
            parts = fp.split("/")
            children.append(
                NoteTreeFolder(key=fp, label=parts[-1], count=cnt)
            )
        # category 总数 = 有 folder_path 的笔记数 + folder_path 为 null 的笔记数
        total = cat_total.get(key, 0)
        nodes.append(
            NoteTreeNode(
                key=key, label=label, code=code,
                count=total, children=children,
            )
        )
    return nodes
