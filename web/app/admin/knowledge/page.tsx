'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { App, Button, Input, Space, Table, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Edit3, Plus, Trash2, FileText, Folder } from 'lucide-react';
import {
  useDeleteKbNote,
  useKbNotes,
  useKbTree,
} from '@/hooks/useAdmin';
import type { KbNoteListItem } from '@/lib/api/admin';
import { formatDate } from '@/lib/utils';

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  private: '私有',
  published: '已发布',
};

const STATUS_COLOR: Record<string, string> = {
  draft: 'default',
  private: 'processing',
  published: 'success',
};

export default function AdminKnowledgePage() {
  const { message, modal } = App.useApp();
  // 选中节点：category（顶层）或 folder_path（子目录）
  const [selected, setSelected] = useState<{
    category: string;
    folder_path?: string; // undefined=整个 category；"null"=无子目录；其他=具体路径
  }>({ category: 'inbox' });
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(50);

  const { data: tree, isLoading: treeLoading } = useKbTree();

  const { data, isLoading, isFetching } = useKbNotes({
    category: selected.category,
    folder_path: selected.folder_path,
    q: q || undefined,
    page,
    size,
  });

  const deleteNote = useDeleteKbNote({
    onSuccess: () => message.success('已删除'),
    onError: (e) => message.error(e.message),
  });

  const columns: ColumnsType<KbNoteListItem> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (_, r) => (
        <div className="min-w-0 flex items-center gap-2">
          {r.is_moc && (
            <Tooltip title="MOC 主题地图">
              <Tag color="gold" className="font-mono">MOC</Tag>
            </Tooltip>
          )}
          <Link
            href={`/admin/knowledge/${r.id}/edit`}
            className="text-on-surface hover:text-primary transition-colors truncate"
            title={r.title}
          >
            {r.title}
          </Link>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => (
        <Tag color={STATUS_COLOR[s] || 'default'} className="font-mono uppercase">
          {STATUS_LABEL[s] || s}
        </Tag>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags: string[]) =>
        tags && tags.length ? (
          <Space size={4} wrap>
            {tags.map((t) => (
              <Tag key={t} className="font-mono">{t}</Tag>
            ))}
          </Space>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 140,
      render: (v: string | null) =>
        v ? (
          <span className="font-mono text-label-mono text-on-surface-variant tabular-nums">
            {formatDate(v)}
          </span>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="编辑">
            <Link href={`/admin/knowledge/${r.id}/edit`}>
              <Button type="text" size="small" icon={<Edit3 size={14} />} />
            </Link>
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="text"
              size="small"
              danger
              icon={<Trash2 size={14} />}
              onClick={() => {
                modal.confirm({
                  title: '删除笔记',
                  content: `确定删除「${r.title}」？该操作不可撤销。`,
                  okText: '删除',
                  okButtonProps: { danger: true },
                  cancelText: '取消',
                  onOk: () => deleteNote.mutateAsync(r.id),
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 当前选中节点标题
  const currentTitle = useMemo(() => {
    if (!tree) return '';
    const node = tree.find((n) => n.key === selected.category);
    if (!node) return '';
    if (!selected.folder_path) return `${node.code} · ${node.label}`;
    const folder = node.children.find((f) => f.key === selected.folder_path);
    return `${node.code}/${folder?.label || selected.folder_path}`;
  }, [tree, selected]);

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
            知识库
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            KNOWLEDGE BASE · 笔记 / 双链 / 模板
          </p>
        </div>
        <Link href="/admin/knowledge/new">
          <Button type="primary" icon={<Plus size={14} />}>
            新建笔记
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
        {/* 左：目录树 */}
        <div className="border border-outline-variant bg-surface-container-lowest p-3 max-h-[70vh] overflow-auto">
          <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest px-2 py-1.5 mb-1">
            目录
          </div>
          {treeLoading ? (
            <div className="text-tertiary-fixed px-2 py-4 text-sm">加载中…</div>
          ) : (
            <div className="space-y-0.5">
              {tree?.map((node) => (
                <div key={node.key}>
                  <button
                    onClick={() => {
                      setSelected({ category: node.key });
                      setPage(1);
                    }}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition-colors ${
                      selected.category === node.key && !selected.folder_path
                        ? 'bg-primary-container text-on-primary-container'
                        : 'hover:bg-surface-container-high'
                    }`}
                  >
                    <Folder size={14} className="shrink-0 text-tertiary-fixed" />
                    <span className="font-mono text-label-mono text-on-surface-variant shrink-0">
                      {node.code}
                    </span>
                    <span className="text-sm truncate flex-1">{node.label}</span>
                    <span className="font-mono text-label-mono text-tertiary-fixed tabular-nums">
                      {node.count}
                    </span>
                  </button>
                  {/* 子目录 */}
                  {node.children.map((f) => (
                    <button
                      key={f.key}
                      onClick={() => {
                        setSelected({ category: node.key, folder_path: f.key });
                        setPage(1);
                      }}
                      className={`w-full flex items-center gap-2 pl-8 pr-2 py-1.5 rounded text-left transition-colors ${
                        selected.folder_path === f.key
                          ? 'bg-primary-container text-on-primary-container'
                          : 'hover:bg-surface-container-high'
                      }`}
                    >
                      <span className="text-sm truncate flex-1">{f.label}</span>
                      <span className="font-mono text-label-mono text-tertiary-fixed tabular-nums">
                        {f.count}
                      </span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 右：笔记列表 */}
        <div className="space-y-3 min-w-0">
          <div className="border border-outline-variant bg-surface-container-lowest p-3 flex flex-wrap gap-3 items-center">
            <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
              {currentTitle}
            </span>
            <Input.Search
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onSearch={() => setPage(1)}
              placeholder="搜索标题/摘要"
              allowClear
              style={{ width: 220 }}
              size="middle"
            />
            <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest ml-auto">
              {data?.total ?? 0} ITEMS
            </span>
          </div>

          <Table<KbNoteListItem>
            rowKey="id"
            columns={columns}
            dataSource={data?.items}
            loading={isLoading || isFetching}
            pagination={{
              current: page,
              pageSize: size,
              total: data?.total ?? 0,
              showSizeChanger: true,
              pageSizeOptions: [20, 50, 100],
              onChange: (p, s) => {
                setPage(p);
                setSize(s);
              },
            }}
            size="middle"
            scroll={{ x: 760 }}
            locale={{
              emptyText: (
                <div className="py-8 text-center">
                  <FileText size={32} className="mx-auto text-tertiary-fixed mb-2" />
                  <p className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                    暂无笔记 · 点击右上角「新建笔记」开始
                  </p>
                </div>
              ),
            }}
          />
        </div>
      </div>
    </div>
  );
}
