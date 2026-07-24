'use client';

import { useEffect, useRef, useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';

export interface WikilinkItem {
  id: string;
  title: string;
}

interface WikilinkSuggestProps {
  visible: boolean;
  items: WikilinkItem[];
  loading: boolean;
  position: { left: number; top: number } | null;
  onSelect: (item: WikilinkItem) => void;
  onClose: () => void;
}

/**
 * 双链输入浮层。输入 [[ 时弹出笔记搜索结果。
 *
 * 键盘：↑/↓ 选择，Enter 确认，Esc 关闭。
 * 鼠标：点击选择。
 *
 * 通过 capture 阶段监听 window keydown 拦截导航键，避免 CodeMirror 收到。
 */
export default function WikilinkSuggest({
  visible,
  items,
  loading,
  position,
  onSelect,
  onClose,
}: WikilinkSuggestProps) {
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // 可见或结果变化时重置高亮
  useEffect(() => {
    setActive(0);
  }, [visible, items]);

  // 键盘导航（capture 拦截，避免 CM 收到）
  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
        setActive((a) => Math.min(a + 1, items.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        e.stopPropagation();
        setActive((a) => Math.max(a - 1, 0));
      } else if (e.key === 'Enter') {
        // 仅当浮层有结果时拦截回车，否则放行给 CM
        if (items[active]) {
          e.preventDefault();
          e.stopPropagation();
          onSelect(items[active]);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [visible, items, active, onSelect, onClose]);

  // 滚动到高亮项
  useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current.children[active] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  if (!visible || !position) return null;

  return (
    <div
      className="fixed z-[1050] w-[300px] max-h-[320px] flex flex-col bg-surface-container-lowest border border-outline-variant rounded-md shadow-lg overflow-hidden"
      style={{ left: position.left, top: position.top }}
    >
      <div className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest px-3 py-1.5 border-b border-outline-variant bg-surface-container-low">
        双链 · {loading ? '搜索中…' : `${items.length} 条`}
      </div>
      <div ref={listRef} className="overflow-auto flex-1">
        {loading && items.length === 0 ? (
          <div className="flex items-center gap-2 px-3 py-3 text-sm text-tertiary-fixed">
            <Loader2 size={14} className="animate-spin" />
            搜索中…
          </div>
        ) : items.length === 0 ? (
          <div className="px-3 py-3 text-sm text-tertiary-fixed">
            无匹配笔记 · 继续输入将创建新链接
          </div>
        ) : (
          items.map((item, i) => (
            <button
              key={item.id}
              type="button"
              onMouseEnter={() => setActive(i)}
              onClick={() => onSelect(item)}
              className={`w-full flex items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors ${
                i === active
                  ? 'bg-primary-container text-on-primary-container'
                  : 'hover:bg-surface-container-high text-on-surface'
              }`}
            >
              <FileText size={13} className="shrink-0 text-tertiary-fixed" />
              <span className="truncate">{item.title}</span>
            </button>
          ))
        )}
      </div>
      <div className="font-mono text-[10px] text-tertiary-fixed uppercase tracking-widest px-3 py-1 border-t border-outline-variant bg-surface-container-low">
        ↑↓ 选择 · Enter 确认 · Esc 关闭
      </div>
    </div>
  );
}
