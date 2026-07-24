'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Button, Input, Modal, Select, Space, Table, Tag, Tooltip, Upload } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload/interface';
import { Edit3, Plus, Trash2, Send, Archive, FileEdit, Upload as UploadIcon } from 'lucide-react';
import { useAdminChannels, useAdminPosts, useDeletePost, useSetPostStatus, useUploadPostMd } from '@/hooks/useAdmin';
import type { AdminPost, PostUploadResult } from '@/lib/api/admin';
import { formatDate } from '@/lib/utils';

const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' },
];

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
  archived: '已归档',
};

const STATUS_COLOR: Record<string, string> = {
  draft: 'default',
  published: 'success',
  archived: 'warning',
};

export default function AdminPostsPage() {
  const { message, modal } = App.useApp();
  const router = useRouter();
  const [filters, setFilters] = useState<{ status: string; channel_id: string; q: string }>({
    status: '',
    channel_id: '',
    q: '',
  });
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);

  // 上传 MD 文件（多文件批量）
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadChannelId, setUploadChannelId] = useState<string>('');
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadResult, setUploadResult] = useState<PostUploadResult | null>(null);

  // 拉频道列表作为筛选项
  const { data: channelsData } = useAdminChannels({ size: 200 });

  // 拉文章列表
  const { data, isLoading, isFetching } = useAdminPosts({
    status: filters.status || undefined,
    channel_id: filters.channel_id || undefined,
    q: filters.q || undefined,
    page,
    size,
  });

  const deletePost = useDeletePost({
    onSuccess: () => message.success('已删除'),
    onError: (e) => message.error(e.message),
  });

  const setStatus = useSetPostStatus({
    onSuccess: (data) => message.success(`已切换为「${STATUS_LABEL[data.status] || data.status}」`),
    onError: (e) => message.error(e.message),
  });

  const uploadPostMd = useUploadPostMd({
    onSuccess: (result) => {
      setUploadResult(result);
      const okCount = result.created.length;
      const failCount = result.failed.length;
      if (failCount === 0) {
        message.success(`全部导入成功：${okCount} 篇草稿已创建`);
      } else if (okCount === 0) {
        message.error(`全部导入失败：${failCount} 个文件`);
      } else {
        message.warning(`部分成功：${okCount} 篇草稿，${failCount} 个失败`);
      }
    },
    onError: (e) => message.error(e.message),
  });

  const channelMap = useMemo(() => {
    const m = new Map<string, { slug: string; name: string }>();
    channelsData?.items.forEach((c) => m.set(c.id, { slug: c.slug, name: c.name }));
    return m;
  }, [channelsData]);

  const columns: ColumnsType<AdminPost> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (_, r) => (
        <div className="min-w-0">
          <Link
            href={`/admin/posts/${r.id}/edit`}
            className="text-on-surface hover:text-primary transition-colors block truncate"
            title={r.title}
          >
            {r.title}
          </Link>
          <div className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest mt-0.5">
            /{r.slug}
          </div>
        </div>
      ),
    },
    {
      title: '频道',
      dataIndex: 'channel_id',
      key: 'channel',
      width: 140,
      render: (cid: string) => {
        const c = channelMap.get(cid);
        return c ? (
          <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
            {c.name}
          </span>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        );
      },
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
      render: (tags: string[] | null) =>
        tags && tags.length ? (
          <Space size={4} wrap>
            {tags.map((t) => (
              <Tag key={t} className="font-mono">
                {t}
              </Tag>
            ))}
          </Space>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '发布时间',
      dataIndex: 'published_at',
      key: 'published_at',
      width: 120,
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
      width: 200,
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="编辑">
            <Link href={`/admin/posts/${r.id}/edit`}>
              <Button type="text" size="small" icon={<Edit3 size={14} />} />
            </Link>
          </Tooltip>
          {r.status !== 'published' && (
            <Tooltip title="发布">
              <Button
                type="text"
                size="small"
                icon={<Send size={14} />}
                onClick={() => setStatus.mutate({ id: r.id, status: 'published' })}
                loading={setStatus.isPending}
              />
            </Tooltip>
          )}
          {r.status === 'published' && (
            <Tooltip title="转草稿">
              <Button
                type="text"
                size="small"
                icon={<FileEdit size={14} />}
                onClick={() => setStatus.mutate({ id: r.id, status: 'draft' })}
                loading={setStatus.isPending}
              />
            </Tooltip>
          )}
          {r.status !== 'archived' && (
            <Tooltip title="归档">
              <Button
                type="text"
                size="small"
                icon={<Archive size={14} />}
                onClick={() => setStatus.mutate({ id: r.id, status: 'archived' })}
                loading={setStatus.isPending}
              />
            </Tooltip>
          )}
          <Tooltip title="删除">
            <Button
              type="text"
              size="small"
              danger
              icon={<Trash2 size={14} />}
              onClick={() => {
                modal.confirm({
                  title: '删除文章',
                  content: `确定删除「${r.title}」？该操作不可撤销。`,
                  okText: '删除',
                  okButtonProps: { danger: true },
                  cancelText: '取消',
                  onOk: () => deletePost.mutateAsync(r.id),
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
            文章管理
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            POSTS · 列表 / 编辑 / 发布
          </p>
        </div>
        <Space>
          <Button icon={<UploadIcon size={14} />} onClick={() => setUploadOpen(true)}>
            批量上传 MD
          </Button>
          <Link href="/admin/posts/new">
            <Button type="primary" icon={<Plus size={14} />}>
              新建文章
            </Button>
          </Link>
        </Space>
      </div>

      {/* Filter bar */}
      <div className="border border-outline-variant bg-surface-container-lowest p-4 mb-4 flex flex-wrap gap-3 items-center">
        <Select
          value={filters.status}
          onChange={(v) => {
            setFilters((f) => ({ ...f, status: v }));
            setPage(1);
          }}
          options={STATUS_OPTIONS}
          style={{ width: 140 }}
          size="middle"
        />
        <Select
          value={filters.channel_id || undefined}
          onChange={(v) => {
            setFilters((f) => ({ ...f, channel_id: v || '' }));
            setPage(1);
          }}
          placeholder="频道"
          allowClear
          style={{ width: 180 }}
          size="middle"
          options={(channelsData?.items || []).map((c) => ({
            label: c.name,
            value: c.id,
          }))}
        />
        <Input.Search
          value={filters.q}
          onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
          onSearch={() => setPage(1)}
          placeholder="搜索标题/摘要"
          allowClear
          style={{ width: 240 }}
          size="middle"
        />
        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest ml-auto">
          {data?.total ?? 0} ITEMS
        </span>
      </div>

      <Table<AdminPost>
        rowKey="id"
        columns={columns}
        dataSource={data?.items}
        loading={isLoading || isFetching}
        pagination={{
          current: page,
          pageSize: size,
          total: data?.total ?? 0,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50],
          onChange: (p, s) => {
            setPage(p);
            setSize(s);
          },
        }}
        size="middle"
        scroll={{ x: 980 }}
      />

      {/* 上传 MD Modal：多文件批量上传 + 结果展示 */}
      <Modal
        title="上传 Markdown 文件"
        open={uploadOpen}
        onCancel={() => {
          setUploadOpen(false);
          setUploadFiles([]);
          setUploadChannelId('');
          setUploadResult(null);
        }}
        width={640}
        footer={
          uploadResult ? (
            <Space>
              <Button
                onClick={() => {
                  // 继续上传：清空结果，回到表单
                  setUploadResult(null);
                  setUploadFiles([]);
                }}
              >
                继续上传
              </Button>
              <Button
                type="primary"
                onClick={() => {
                  setUploadOpen(false);
                  setUploadFiles([]);
                  setUploadChannelId('');
                  setUploadResult(null);
                  // 跳转到第一篇草稿的编辑页（若有）
                  const first = uploadResult.created[0];
                  if (first) {
                    router.push(`/admin/posts/${first.id}/edit`);
                  }
                }}
              >
                {uploadResult.created.length > 0
                  ? `编辑第一篇（${uploadResult.created.length} 篇草稿）`
                  : '完成'}
              </Button>
            </Space>
          ) : (
            <Space>
              <Button
                onClick={() => {
                  setUploadOpen(false);
                  setUploadFiles([]);
                  setUploadChannelId('');
                }}
              >
                取消
              </Button>
              <Button
                type="primary"
                onClick={() => {
                  if (uploadFiles.length === 0) {
                    message.warning('请选择 .md 文件');
                    return;
                  }
                  if (!uploadChannelId) {
                    message.warning('请选择频道');
                    return;
                  }
                  uploadPostMd.mutate({
                    files: uploadFiles,
                    channelId: uploadChannelId,
                  });
                }}
                loading={uploadPostMd.isPending}
                disabled={uploadFiles.length === 0 || !uploadChannelId}
              >
                {`解析并创建草稿${uploadFiles.length > 0 ? `（${uploadFiles.length} 个文件）` : ''}`}
              </Button>
            </Space>
          )
        }
      >
        {uploadResult ? (
          /* 上传结果展示：created + failed */
          <div className="space-y-4 py-2">
            {uploadResult.created.length > 0 && (
              <div>
                <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-2">
                  {`成功创建草稿（${uploadResult.created.length}）`}
                </div>
                <div className="space-y-1 max-h-48 overflow-auto">
                  {uploadResult.created.map((p) => (
                    <Link
                      key={p.id}
                      href={`/admin/posts/${p.id}/edit`}
                      className="flex items-center justify-between gap-2 px-3 py-1.5 bg-surface-container-lowest border border-outline-variant hover:border-primary transition-colors"
                    >
                      <span className="truncate text-on-surface text-sm">
                        {p.title}
                      </span>
                      <span className="font-mono text-label-mono text-tertiary-fixed shrink-0">
                        /{p.slug}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
            {uploadResult.failed.length > 0 && (
              <div>
                <div className="font-mono text-label-mono text-error uppercase tracking-widest mb-2">
                  {`导入失败（${uploadResult.failed.length}）`}
                </div>
                <div className="space-y-1 max-h-48 overflow-auto">
                  {uploadResult.failed.map((item, i) => (
                    <div
                      key={`${item.filename}-${i}`}
                      className="px-3 py-1.5 bg-surface-container-lowest border border-outline-variant"
                    >
                      <div className="text-on-surface text-sm truncate">
                        {item.filename}
                      </div>
                      <div className="font-mono text-label-mono text-error mt-0.5">
                        {item.reason}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* 文件选择表单 */
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
              <Upload.Dragger
                multiple
                maxCount={20}
                accept=".md,.markdown"
                beforeUpload={(file) => {
                  // 客户端预校验：扩展名 + 大小（5MB）
                  const name = file.name.toLowerCase();
                  const isMd = name.endsWith('.md') || name.endsWith('.markdown');
                  if (!isMd) {
                    message.error(`${file.name}: 仅支持 .md / .markdown`);
                    return Upload.LIST_IGNORE;
                  }
                  if (file.size > 5 * 1024 * 1024) {
                    message.error(
                      `${file.name}: 文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB > 5MB）`,
                    );
                    return Upload.LIST_IGNORE;
                  }
                  setUploadFiles((prev) => [...prev, file]);
                  return false; // 阻止自动上传，由 Modal 按钮统一提交
                }}
                onRemove={(file: UploadFile) => {
                  const key = `${file.name}-${file.size}`;
                  setUploadFiles((prev) =>
                    prev.filter((f) => `${f.name}-${f.size}` !== key),
                  );
                }}
                fileList={uploadFiles.map((f) => ({
                  uid: `${f.name}-${f.size}`,
                  name: f.name,
                  size: f.size,
                  status: 'done' as const,
                }))}
              >
                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint font-mono text-label-mono text-tertiary-fixed">
                  仅支持 .md / .markdown，单文件 ≤ 5MB，UTF-8 编码，最多 20 个
                </p>
              </Upload.Dragger>
              <div className="font-mono text-label-mono text-tertiary-fixed mt-2">
                上传后创建为草稿（不触发发布和 RAG 入库），可在编辑页修改后发布
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
