'use client';

import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

/**
 * 文章元信息抽屉浮层（纯原生 HTML 表单，不使用 Antd 组件）。
 *
 * 与 MetaDrawer（笔记）对应，但仅包含文章字段：
 * 状态 / 频道 / Slug / 标签 / 摘要 / 阅读时长。
 *
 * Antd 的 Select/Input 在 hidden/visible 切换时内部 hooks 会导致
 * "Rendered more hooks" 错误，因此改用原生元素 + form.setFieldValue。
 */

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' },
];

export interface PostMetaValues {
  status: string;
  channel_id?: string;
  slug: string;
  tags: string[];
  excerpt: string;
  reading_time?: number | null;
}

interface PostMetaDrawerProps {
  visible: boolean;
  onClose: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  form: any;
  /** 当前表单值（由父组件传入，避免 render 阶段调 form.getFieldValue） */
  values: PostMetaValues;
  /** 字段变化回调（同步到父组件 state） */
  onFieldChange: (field: string, value: unknown) => void;
  channels: { id: string; name: string }[];
  channelsLoading: boolean;
  isEdit: boolean;
  slugTouchedRef: React.MutableRefObject<boolean>;
  triggerRef: React.RefObject<HTMLElement>;
}

export default function PostMetaDrawer({
  visible,
  onClose,
  form,
  values,
  onFieldChange,
  channels,
  channelsLoading,
  isEdit,
  slugTouchedRef,
  triggerRef,
}: PostMetaDrawerProps) {
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
          META · 文章元信息
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
            disabled={channelsLoading}
          >
            <option value="">选择频道（发布必填）</option>
            {channels.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
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
          <p className="font-mono text-label-mono text-tertiary-fixed mt-1">
            {isEdit ? '修改后保存生效' : '留空则从标题自动生成'}
          </p>
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

        {/* 阅读时长 */}
        <div>
          <label className={labelCls}>阅读时长（分）</label>
          <input
            type="number"
            min={0}
            max={300}
            className={inputCls}
            value={v.reading_time ?? ''}
            placeholder="自动计算"
            onChange={(e) => {
              const val = e.target.value;
              setField(
                'reading_time',
                val === '' ? null : Number(val),
              );
            }}
          />
          <p className="font-mono text-label-mono text-tertiary-fixed mt-1">
            留空则按字数自动计算
          </p>
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
