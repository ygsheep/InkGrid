'use client';

import { Link2, FileText } from 'lucide-react';

/**
 * 编辑器底部状态条。
 *
 * 仅显示字数 / 阅读时长 / 出链数 / 反链数。
 * 主操作（创建/保存）按钮位于顶部条，底部不再放置按钮。
 * 参考 Obsidian 的底部状态条。
 */

interface EditorStatusBarProps {
  /** 字数（中文按字，英文按词） */
  wordCount: number;
  /** 阅读时长（分钟） */
  readingTime: number;
  /** 出链数 */
  outlinksCount: number;
  /** 反链数 */
  backlinksCount: number;
  /** 自动保存状态 */
  autoSaveStatus: 'idle' | 'pending' | 'saving' | 'saved';
  /** 是否编辑模式 */
  isEdit: boolean;
  /** 提交中（保留接口兼容，底部不再使用） */
  submitting?: boolean;
  /** 保存/发布回调（保留接口兼容，底部不再使用） */
  onSubmit?: () => void;
}

export default function EditorStatusBar({
  wordCount,
  readingTime,
  outlinksCount,
  backlinksCount,
  isEdit,
}: EditorStatusBarProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2 border-t border-outline-variant bg-surface-container-lowest">
      {/* 左侧：统计 */}
      <div className="flex items-center gap-4 font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
        <Stat label="字数" value={wordCount.toLocaleString()} />
        <Divider />
        <Stat label="阅读" value={`${readingTime}min`} />
        <Divider />
        <Stat
          label="出链"
          value={outlinksCount}
          icon={<Link2 size={11} className="text-tertiary-fixed" />}
          valueClass="text-tertiary-fixed"
        />
        {isEdit && (
          <>
            <Divider />
            <Stat
              label="反链"
              value={backlinksCount}
              icon={<FileText size={11} className="text-tertiary-fixed" />}
            />
          </>
        )}
      </div>

      {/* 右侧：占位（主操作按钮已移至顶部条） */}
      <div className="font-mono text-label-mono text-outline uppercase tracking-widest">
        {isEdit ? 'ESC 退出全屏 · Ctrl+S 保存' : '输入正文后自动创建'}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
  valueClass = 'text-on-surface',
}: {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  valueClass?: string;
}) {
  return (
    <span className="flex items-center gap-1.5">
      {icon}
      <span>{label}</span>
      <span className={`tabular-nums font-medium ${valueClass}`}>{value}</span>
    </span>
  );
}

function Divider() {
  return <span className="w-px h-3 bg-outline-variant" />;
}
