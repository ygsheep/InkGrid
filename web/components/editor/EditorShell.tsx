'use client';

import { cn } from '@/lib/utils';

interface EditorShellProps {
  /** 顶部条内容（返回按钮、面包屑、保存状态、META 按钮、状态徽章、主操作按钮等） */
  topBar: React.ReactNode;
  /** 底部状态条内容（字数/阅读/出链/反链统计） */
  bottomBar?: React.ReactNode;
  /** 写作区内容（hero 标题 + 全宽编辑器） */
  children: React.ReactNode;
  /** 外层容器额外 className */
  className?: string;
}

/**
 * 编辑器三段式布局（参考 Notion / Obsidian）。
 *
 * - 顶部条：固定高度，返回 / 面包屑 / 状态 / 操作按钮
 * - 写作区：flex-1 可滚动，占满宽度
 * - 底部条：固定高度，统计信息
 *
 * 由 NoteEditor / PostEditor 共用，确保布局一致。
 */
export default function EditorShell({
  topBar,
  bottomBar,
  children,
  className,
}: EditorShellProps) {
  return (
    <div
      className={cn(
        'flex flex-col h-[calc(100vh-64px)]',
        className,
      )}
    >
      {/* 顶部条 */}
      <div className="relative flex items-center justify-between px-4 py-2.5 border-b border-outline-variant bg-surface-container-lowest shrink-0">
        {topBar}
      </div>

      {/* 写作区（可滚动） */}
      <div className="flex-1 overflow-auto bg-background min-h-0">
        {children}
      </div>

      {/* 底部状态条 */}
      {bottomBar && <div className="shrink-0">{bottomBar}</div>}
    </div>
  );
}
