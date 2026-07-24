'use client';

import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

/**
 * 元信息抽屉浮层（纯原生 HTML 表单，不使用 Antd 组件）。
 *
 * Antd 的 Select/Input 在 hidden/visible 切换时内部 hooks 会导致
 * "Rendered more hooks" 错误，因此改用原生元素 + form.setFieldValue。
 */

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '私有', value: 'private' },
  { label: '已发布', value: 'published' },
];

const CATEGORY_OPTIONS = [
  { label: '00 收集箱', value: 'inbox' },
  { label: '01 每日笔记', value: 'daily' },
  { label: '02 阅读笔记', value: 'reading' },
  { label: '03 主题知识', value: 'knowledge' },
  { label: '04 项目资料', value: 'projects' },
  { label: '05 模板库', value: 'templates' },
];

interface MetaDrawerProps {
  visible: boolean;
  onClose: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  form: any;
  /** 当前表单值（由父组件传入，避免 render 阶段调 form.getFieldValue） */
  values: {
    status: string;
    channel_id?: string;
    category: string;
    folder_path?: string;
    slug: string;
    tags: string[];
    is_moc: boolean;
    source_url?: string;
    excerpt?: string;
  };
  /** 字段变化回调（同步到父组件 state） */
  onFieldChange: (field: string, value: unknown) => void;
  channels: { id: string; name: string }[];
  channelsLoading: boolean;
  templates?: { id: string; name: string; category: string }[];
  onTemplateSelect?: (templateId: string) => void;
  isEdit: boolean;
  slugTouchedRef: React.MutableRefObject<boolean>;
  triggerRef: React.RefObject<HTMLElement>;
}

export default function MetaDrawer({
  visible,
  onClose,
  form,
  values,
  onFieldChange,
  channels,
  channelsLoading,
  templates,
  onTemplateSelect,
  isEdit,
  slugTouchedRef,
  triggerRef,
}: MetaDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!visible) return;
    const onDocClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        drawerRef.current?.contains(target) ||
        triggerRef.current?.contains(target)
      ) {
        return;
      }
      onClose();
    };
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', onDocClick);
    }, 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', onDocClick);
    };
  }, [visible, onClose, triggerRef]);

  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [visible, onClose]);

  // 不在 render 阶段调 form.getFieldValue（会导致 React 错误），改用传入的 values
  const v = values;

  // 统一字段更新：同时写 form 和通知父组件
  const setField = (field: string, value: unknown) => {
    form.setFieldValue(field, value);
    onFieldChange(field, value);
  };

  const inputCls =
    'w-full bg-surface border border-outline-variant px-2 py-1 text-sm text-on-surface focus:outline-none focus:border-primary mt-1';
  const labelCls =
    'font-mono text-label-mono text-on-surface-variant uppercase tracking-widest';

  return (
    <div
      ref={drawerRef}
      className={`absolute top-full right-0 mt-1 w-[280px] max-h-[70vh] overflow-auto bg-surface-container-lowest border border-outline z-50 ${
        visible ? '' : 'hidden'
      }`}
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-outline-variant">
        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
          META · 元信息
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-on-surface-variant hover:text-primary transition-colors"
          aria-label="关闭"
        >
          <X size={14} />
        </button>
      </div>

      <div className="p-3 space-y-3">
        {/* 模板 */}
        {!isEdit && templates && templates.length > 0 && (
          <div>
            <label className={labelCls}>套用模板</label>
            <select
              className={inputCls}
              defaultValue=""
              onChange={(e) => {
                if (e.target.value && onTemplateSelect) onTemplateSelect(e.target.value);
              }}
            >
              <option value="">选择模板填充正文</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}（{t.category}）
                </option>
              ))}
            </select>
          </div>
        )}

        {/* 状态 */}
        <div>
          <label className={labelCls}>状态</label>
          <select
            className={inputCls}
            value={v.status || 'draft'}
            onChange={(e) => setField('status', e.target.value)}
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* 频道 */}
        <div>
          <label className={labelCls}>频道</label>
          <select
            className={inputCls}
            value={v.channel_id || ''}
            onChange={(e) => setField('channel_id', e.target.value || undefined)}
          >
            <option value="">选择频道（发布必填）</option>
            {channels.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {/* 分类目录 */}
        <div>
          <label className={labelCls}>分类目录</label>
          <select
            className={inputCls}
            value={v.category || 'inbox'}
            onChange={(e) => setField('category', e.target.value)}
          >
            {CATEGORY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* 子目录 */}
        <div>
          <label className={labelCls}>子目录</label>
          <input
            type="text"
            className={inputCls}
            value={v.folder_path || ''}
            placeholder="knowledge/大模型"
            onChange={(e) => setField('folder_path', e.target.value)}
          />
        </div>

        {/* Slug */}
        <div>
          <label className={labelCls}>Slug</label>
          <input
            type="text"
            className={inputCls}
            value={v.slug || ''}
            placeholder="url-friendly-slug"
            onChange={(e) => {
              slugTouchedRef.current = true;
              setField('slug', e.target.value);
            }}
          />
        </div>

        {/* 标签 */}
        <div>
          <label className={labelCls}>标签（逗号分隔）</label>
          <input
            type="text"
            className={inputCls}
            value={(v.tags || []).join(', ')}
            placeholder="标签1, 标签2"
            onChange={(e) => {
              const tags = e.target.value
                .split(/[,\s]+/)
                .filter(Boolean);
              setField('tags', tags);
            }}
          />
        </div>

        {/* MOC */}
        <div>
          <label className={labelCls}>MOC 主题地图</label>
          <select
            className={inputCls}
            value={v.is_moc ? 'true' : 'false'}
            onChange={(e) => setField('is_moc', e.target.value === 'true')}
          >
            <option value="false">否</option>
            <option value="true">是（主题地图节点）</option>
          </select>
        </div>

        {/* 来源 URL */}
        <div>
          <label className={labelCls}>来源 URL</label>
          <input
            type="text"
            className={inputCls}
            value={v.source_url || ''}
            placeholder="https://..."
            onChange={(e) => setField('source_url', e.target.value)}
          />
        </div>

        {/* 摘要 */}
        <div>
          <label className={labelCls}>摘要</label>
          <textarea
            className={`${inputCls} resize-none`}
            rows={3}
            value={v.excerpt || ''}
            placeholder="一行简介（留空自动生成）"
            onChange={(e) => setField('excerpt', e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
