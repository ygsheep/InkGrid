'use client';

import { useState } from 'react';
import {
  App,
  Button,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Upload,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload/interface';
import {
  Download,
  RefreshCw,
  Trash2,
  Upload as UploadIcon,
  Zap,
} from 'lucide-react';
import {
  useAdminChannels,
  useDeleteKnowledgeDoc,
  useDownloadKnowledgeDoc,
  useKnowledgeDocs,
  useRebuildKnowledge,
  useReindexKnowledgeDoc,
  useUploadKnowledgeDoc,
} from '@/hooks/useAdmin';
import type { UploadResult } from '@/lib/api/admin';
import type { KnowledgeDoc } from '@/lib/api/admin';
import { formatDate } from '@/lib/utils';

const SOURCE_OPTIONS = [
  { label: '全部来源', value: '' },
  { label: '文章', value: 'article' },
  { label: '上传文档', value: 'upload' },
  { label: '政策', value: 'policy' },
];

const SOURCE_LABEL: Record<string, string> = {
  article: '文章',
  upload: '上传',
  policy: '政策',
};

const STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '已入库', value: 'indexed' },
  { label: '部分成功', value: 'partial' },
  { label: '排队中', value: 'pending' },
  { label: '失败', value: 'failed' },
];

const STATUS_LABEL: Record<string, string> = {
  pending: '排队中',
  indexed: '已入库',
  partial: '部分成功',
  failed: '失败',
};

const STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  indexed: 'success',
  partial: 'warning',
  failed: 'error',
};

const FORMAT_LABEL: Record<string, string> = {
  md: 'MD',
  txt: 'TXT',
  pdf: 'PDF',
  docx: 'DOCX',
};

const FORMAT_COLOR: Record<string, string> = {
  md: 'blue',
  txt: 'default',
  pdf: 'red',
  docx: 'geekblue',
};

// 各格式大小上限（与后端 upload_security.MAX_SIZE_BY_FORMAT 对齐）
const MAX_SIZE_BY_FORMAT: Record<string, number> = {
  md: 5 * 1024 * 1024,
  txt: 5 * 1024 * 1024,
  pdf: 20 * 1024 * 1024,
  docx: 20 * 1024 * 1024,
};

// 扩展名 → source_format
const EXT_TO_FORMAT: Record<string, string> = {
  '.md': 'md',
  '.markdown': 'md',
  '.txt': 'txt',
  '.pdf': 'pdf',
  '.docx': 'docx',
};

/** 格式化文件大小 */
function formatSize(bytes: number | null | undefined): string {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** 从文件名提取 source_format */
function detectFormat(filename: string): string | null {
  const dotIdx = filename.lastIndexOf('.');
  if (dotIdx < 0) return null;
  const ext = filename.slice(dotIdx).toLowerCase();
  return EXT_TO_FORMAT[ext] ?? null;
}

/** 客户端预校验单个文件（与后端校验对齐，提前拦截明显错误） */
function validateFile(file: File): string | null {
  const fmt = detectFormat(file.name);
  if (!fmt) {
    return `不支持的扩展名（仅支持 .md/.txt/.pdf/.docx）`;
  }
  const max = MAX_SIZE_BY_FORMAT[fmt];
  if (file.size > max) {
    return `文件过大（${formatSize(file.size)} > ${max / 1024 / 1024}MB）`;
  }
  return null;
}

export default function AdminKnowledgePage() {
  const { message, modal } = App.useApp();
  const [filters, setFilters] = useState<{
    source_type: string;
    status: string;
    channel_id: string;
    q: string;
  }>({ source_type: '', status: '', channel_id: '', q: '' });
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);

  // 上传 Modal 状态
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadChannelId, setUploadChannelId] = useState<string>('');
  const [uploadTitle, setUploadTitle] = useState<string>('');
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  // 频道下拉（筛选项 + 上传 Modal 共用）
  const { data: channelsData } = useAdminChannels({ size: 200 });

  // 知识库文档列表
  const { data, isLoading, isFetching } = useKnowledgeDocs({
    source_type: filters.source_type || undefined,
    status: filters.status || undefined,
    channel_id: filters.channel_id || undefined,
    q: filters.q || undefined,
    page,
    size,
  });

  const uploadDoc = useUploadKnowledgeDoc({
    onSuccess: (result) => {
      setUploadResult(result);
      const okCount = result.created.length;
      const failCount = result.failed.length;
      if (failCount === 0) {
        message.success(`全部上传成功：${okCount} 个文档已入库`);
      } else if (okCount === 0) {
        message.error(`全部上传失败：${failCount} 个文件`);
      } else {
        message.warning(`部分成功：${okCount} 成功，${failCount} 失败`);
      }
    },
    onError: (e) => message.error(e.message),
  });

  const deleteDoc = useDeleteKnowledgeDoc({
    onSuccess: () => message.success('文档已删除'),
    onError: (e) => message.error(e.message),
  });

  const downloadDoc = useDownloadKnowledgeDoc({
    onSuccess: ({ blob, filename }) => {
      // 触发浏览器下载
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    onError: (e) => message.error(e.message),
  });

  const reindexDoc = useReindexKnowledgeDoc({
    onSuccess: () => message.success('重建任务已派发，3 秒后刷新列表'),
    onError: (e) => message.error(e.message),
  });

  const rebuildAll = useRebuildKnowledge({
    onSuccess: () => message.success('全量重建任务已派发，5 秒后刷新列表'),
    onError: (e) => message.error(e.message),
  });

  const columns: ColumnsType<KnowledgeDoc> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (_, r) => (
        <div className="min-w-0">
          <div className="text-on-surface truncate" title={r.title}>
            {r.title}
          </div>
          {r.original_filename && (
            <div
              className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest mt-0.5 truncate"
              title={r.original_filename}
            >
              {r.original_filename}
            </div>
          )}
        </div>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 90,
      render: (s: string) => (
        <Tag className="font-mono uppercase">{SOURCE_LABEL[s] || s}</Tag>
      ),
    },
    {
      title: '格式',
      dataIndex: 'source_format',
      key: 'source_format',
      width: 80,
      render: (fmt: string | null) =>
        fmt ? (
          <Tag color={FORMAT_COLOR[fmt] || 'default'} className="font-mono uppercase">
            {FORMAT_LABEL[fmt] || fmt}
          </Tag>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '频道',
      key: 'channel',
      width: 140,
      render: (_, r) =>
        r.channel_name ? (
          <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
            {r.channel_name}
          </span>
        ) : (
          <span className="text-tertiary-fixed">—</span>
        ),
    },
    {
      title: '大小',
      dataIndex: 'source_size',
      key: 'source_size',
      width: 90,
      render: (n: number | null) => (
        <span className="font-mono text-label-mono text-on-surface-variant tabular-nums">
          {formatSize(n)}
        </span>
      ),
    },
    {
      title: '分片',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 70,
      render: (n: number) => (
        <span className="font-mono text-on-surface-variant tabular-nums">{n}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (s: string) => (
        <Tooltip
          title={s === 'failed' || s === 'partial' ? '展开查看错误信息' : undefined}
        >
          <Tag color={STATUS_COLOR[s] || 'default'} className="font-mono uppercase">
            {STATUS_LABEL[s] || s}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
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
      width: 150,
      render: (_, r) => (
        <Space size={4}>
          {r.source_type === 'upload' && r.raw_uri && (
            <Tooltip title="下载源文件">
              <Button
                type="text"
                size="small"
                icon={<Download size={14} />}
                loading={downloadDoc.isPending}
                onClick={() => downloadDoc.mutate(r.id)}
              />
            </Tooltip>
          )}
          <Tooltip title="重建向量">
            <Button
              type="text"
              size="small"
              icon={<RefreshCw size={14} />}
              loading={reindexDoc.isPending}
              onClick={() => {
                modal.confirm({
                  title: '重建向量',
                  content: `确定对「${r.title}」重新分块 + 生成向量？已有向量会被覆盖。`,
                  okText: '重建',
                  cancelText: '取消',
                  onOk: () => reindexDoc.mutateAsync(r.id),
                });
              }}
            />
          </Tooltip>
          {r.source_type === 'upload' && (
            <Tooltip title="删除文档">
              <Button
                type="text"
                size="small"
                danger
                icon={<Trash2 size={14} />}
                loading={deleteDoc.isPending}
                onClick={() => {
                  modal.confirm({
                    title: '删除文档',
                    content: `确定删除「${r.title}」？将同时清理源文件、分片与向量，不可恢复。`,
                    okText: '删除',
                    okButtonProps: { danger: true },
                    cancelText: '取消',
                    onOk: () => deleteDoc.mutateAsync(r.id),
                  });
                }}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // 错误信息展开行（partial / failed 时显示）
  const expandable = {
    rowExpandable: (r: KnowledgeDoc) =>
      r.status === 'failed' || r.status === 'partial',
    expandedRowRender: (r: KnowledgeDoc) => (
      <div className="px-4 py-2">
        <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-1">
          错误信息
        </div>
        <pre className="font-mono text-label-mono text-error bg-surface-container-lowest p-3 overflow-auto">
          {r.error_msg || '(无)'}
        </pre>
      </div>
    ),
  };

  // ===== 上传 Modal 相关 =====

  const resetUploadState = () => {
    setUploadFiles([]);
    setUploadChannelId('');
    setUploadTitle('');
    setUploadResult(null);
  };

  const closeUploadModal = () => {
    setUploadOpen(false);
    resetUploadState();
  };

  // Upload.Dragger 的 props：选择文件时客户端预校验，拒绝非法文件
  const uploadProps = {
    multiple: true,
    maxCount: 20,
    accept: '.md,.markdown,.txt,.pdf,.docx',
    beforeUpload: (file: File) => {
      const err = validateFile(file);
      if (err) {
        message.error(`${file.name}: ${err}`);
        return Upload.LIST_IGNORE;
      }
      setUploadFiles((prev) => [...prev, file]);
      return false; // 阻止自动上传，手动收集后统一提交
    },
    onRemove: (file: UploadFile) => {
      // 用 name+size 作为稳定标识匹配回原始 File
      const key = `${file.name}-${file.size}`;
      setUploadFiles((prev) => prev.filter((f) => `${f.name}-${f.size}` !== key));
    },
    fileList: uploadFiles.map((f) => ({
      uid: `${f.name}-${f.size}`,
      name: f.name,
      size: f.size,
      status: 'done' as const,
    })),
  };

  const handleUploadSubmit = () => {
    if (uploadFiles.length === 0) {
      message.warning('请选择文件');
      return;
    }
    if (!uploadChannelId) {
      message.warning('请选择频道');
      return;
    }
    uploadDoc.mutate({
      files: uploadFiles,
      channelId: uploadChannelId,
      title: uploadTitle || undefined,
    });
  };

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
            知识库
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            KNOWLEDGE · 文档入库 / 向量状态 / 重建
          </p>
        </div>
        <Space>
          <Button
            icon={<UploadIcon size={14} />}
            onClick={() => setUploadOpen(true)}
          >
            上传文档
          </Button>
          <Button
            icon={<Zap size={14} />}
            onClick={() => {
              modal.confirm({
                title: '全量重建',
                content:
                  '将遍历所有已发布文章，删除旧向量并重新入库。期间 RAG 检索可能不完整，且会占用 worker 较长时间。确定继续？',
                okText: '全量重建',
                okButtonProps: { danger: true },
                cancelText: '取消',
                onOk: () => rebuildAll.mutateAsync(),
              });
            }}
            loading={rebuildAll.isPending}
          >
            全量重建
          </Button>
        </Space>
      </div>

      {/* Filter bar */}
      <div className="border border-outline-variant bg-surface-container-lowest p-4 mb-4 flex flex-wrap gap-3 items-center">
        <Select
          value={filters.source_type}
          onChange={(v) => {
            setFilters((f) => ({ ...f, source_type: v }));
            setPage(1);
          }}
          options={SOURCE_OPTIONS}
          style={{ width: 140 }}
          size="middle"
        />
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
          placeholder="搜索标题"
          allowClear
          style={{ width: 240 }}
          size="middle"
        />
        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest ml-auto">
          {data?.total ?? 0} ITEMS
        </span>
      </div>

      <Table<KnowledgeDoc>
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
        scroll={{ x: 1100 }}
        expandable={expandable}
      />

      {/* 上传 Modal：多格式多文件上传 + 结果展示 */}
      <Modal
        title="上传知识库文档"
        open={uploadOpen}
        onCancel={closeUploadModal}
        width={640}
        footer={
          uploadResult ? (
            <Button onClick={closeUploadModal}>完成</Button>
          ) : (
            <Space>
              <Button onClick={closeUploadModal}>取消</Button>
              <Button
                type="primary"
                onClick={handleUploadSubmit}
                loading={uploadDoc.isPending}
                disabled={uploadFiles.length === 0 || !uploadChannelId}
              >
                {`解析并入库${uploadFiles.length > 0 ? `（${uploadFiles.length} 个文件）` : ''}`}
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
                  {`成功入库（${uploadResult.created.length}）`}
                </div>
                <div className="space-y-1 max-h-48 overflow-auto">
                  {uploadResult.created.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between gap-2 px-3 py-1.5 bg-surface-container-lowest border border-outline-variant"
                    >
                      <span className="truncate text-on-surface text-sm">
                        {doc.title}
                      </span>
                      <Tag
                        color={STATUS_COLOR[doc.status] || 'default'}
                        className="font-mono uppercase shrink-0"
                      >
                        {STATUS_LABEL[doc.status] || doc.status}
                      </Tag>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {uploadResult.failed.length > 0 && (
              <div>
                <div className="font-mono text-label-mono text-error uppercase tracking-widest mb-2">
                  {`上传失败（${uploadResult.failed.length}）`}
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
            {uploadFiles.length === 1 && (
              <div>
                <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-2">
                  标题（可选）
                </div>
                <Input
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="留空则从内容/文件名提取"
                />
              </div>
            )}
            <div>
              <div className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-2">
                文档文件
              </div>
              <Upload.Dragger {...uploadProps}>
                <p className="ant-upload-text">
                  点击或拖拽文件到此区域上传
                </p>
                <p className="ant-upload-hint font-mono text-label-mono text-tertiary-fixed">
                  支持 .md / .txt / .pdf / .docx，单文件 ≤ 5MB（PDF/DOCX ≤ 20MB），最多 20 个
                </p>
              </Upload.Dragger>
              <div className="font-mono text-label-mono text-tertiary-fixed mt-2">
                上传后同步入库（解析 / 分块 / embedding / 向量写入），大文件可能耗时较长
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
