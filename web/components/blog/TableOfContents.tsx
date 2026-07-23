'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { TocItem } from '@/types';

/**
 * Table of Contents — 右侧 sticky 导航。
 *
 * - 顶部有整体折叠按钮，可收起/展开整个目录
 * - 每个 h2 父级可折叠其下的 h3 子项
 * - 折叠状态持久化到 localStorage
 * - 点击锚点平滑滚动到对应标题
 */
const ALL_COLLAPSED_KEY = 'toc-all-collapsed';
const PARENTS_COLLAPSED_KEY = 'toc-parents-collapsed';

export default function TableOfContents({ items }: { items: TocItem[] }) {
  const [allCollapsed, setAllCollapsed] = useState(false);
  const [collapsedParents, setCollapsedParents] = useState<Set<string>>(new Set());
  const [hydrated, setHydrated] = useState(false);

  // 初始化读取持久化偏好
  useEffect(() => {
    try {
      const all = localStorage.getItem(ALL_COLLAPSED_KEY);
      if (all === '1') setAllCollapsed(true);

      const parents = localStorage.getItem(PARENTS_COLLAPSED_KEY);
      if (parents) {
        const arr = JSON.parse(parents);
        if (Array.isArray(arr)) setCollapsedParents(new Set(arr));
      }
    } catch {
      // 隐私模式 / localStorage 被禁用，静默降级
    }
    setHydrated(true);
  }, []);

  // 折叠状态变化时持久化
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(ALL_COLLAPSED_KEY, allCollapsed ? '1' : '0');
      localStorage.setItem(
        PARENTS_COLLAPSED_KEY,
        JSON.stringify(Array.from(collapsedParents)),
      );
    } catch {
      // 静默失败
    }
  }, [allCollapsed, collapsedParents, hydrated]);

  if (!items?.length) return null;

  // 按 h2 分组：每个 h2 后跟随其下的 h3，直到下一个 h2
  const groups: { parent: TocItem; children: TocItem[] }[] = [];
  let currentParent: TocItem | null = null;
  for (const item of items) {
    if (item.level === 2) {
      currentParent = item;
      groups.push({ parent: item, children: [] });
    } else if (item.level === 3 && currentParent) {
      groups[groups.length - 1].children.push(item);
    }
  }

  const toggleParent = (id: string) => {
    setCollapsedParents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // 平滑滚动到对应标题
  const handleNavigate = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // 同步 URL hash（方便分享 / 后退）
      history.replaceState(null, '', `#${id}`);
    }
  };

  return (
    <nav>
      <div className="flex items-center justify-between mb-3">
        <p className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
          目录 · INDEX
        </p>
        <button
          onClick={() => setAllCollapsed((v) => !v)}
          aria-label={allCollapsed ? '展开目录' : '收起目录'}
          className="text-on-surface-variant hover:text-primary transition-colors"
        >
          {allCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
        </button>
      </div>

      {!allCollapsed && (
        <ul className="space-y-2 border-l border-outline-variant">
          {groups.map(({ parent, children }) => {
            const parentCollapsed = collapsedParents.has(parent.id);
            const hasChildren = children.length > 0;
            return (
              <li key={parent.id} style={{ paddingLeft: 12 }}>
                <div className="flex items-center -ml-px">
                  {hasChildren ? (
                    <button
                      onClick={() => toggleParent(parent.id)}
                      aria-label={parentCollapsed ? '展开子项' : '收起子项'}
                      className="text-tertiary-fixed hover:opacity-80 transition-opacity mr-1 flex items-center shrink-0"
                    >
                      {parentCollapsed ? <ChevronRight size={10} /> : <ChevronDown size={10} />}
                    </button>
                  ) : (
                    <span className="inline-block w-[10px] mr-1 shrink-0" />
                  )}
                  <a
                    href={`#${parent.id}`}
                    onClick={(e) => handleNavigate(e, parent.id)}
                    className="block border-l border-transparent pl-3 text-on-surface hover:text-primary hover:border-tertiary-fixed transition-colors text-body-sm leading-relaxed"
                  >
                    {parent.title}
                  </a>
                </div>

                {hasChildren && !parentCollapsed && (
                  <ul className="mt-1 space-y-1">
                    {children.map((child) => (
                      <li key={child.id} style={{ paddingLeft: 20 }}>
                        <a
                          href={`#${child.id}`}
                          onClick={(e) => handleNavigate(e, child.id)}
                          className="block -ml-px border-l border-transparent pl-3 text-on-surface-variant hover:text-primary hover:border-tertiary-fixed transition-colors text-body-sm leading-relaxed"
                        >
                          {child.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
