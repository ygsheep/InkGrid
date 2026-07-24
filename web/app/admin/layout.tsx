'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  BookOpen,
  Layers,
  Bot,
  Database,
  Settings,
  LogOut,
  Menu as MenuIcon,
  X,
  Loader2,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMe, useLogout } from '@/hooks/useAdmin';
import { App } from 'antd';

const menu = [
  { href: '/admin', label: '看板', icon: LayoutDashboard },
  { href: '/admin/posts', label: '文章', icon: FileText },
  { href: '/admin/knowledge', label: '知识库', icon: BookOpen },
  { href: '/admin/qa', label: '问题审核', icon: MessageSquareText },
  { href: '/admin/channels', label: '频道', icon: Layers },
  { href: '/admin/persona', label: '人设', icon: Bot },
  { href: '/admin/policy-collector', label: '政策采集', icon: Database },
  { href: '/admin/settings', label: '设置', icon: Settings },
];

/** 编辑器类页面：突破 main 的 max-width 与 padding，让写作区占满宽度 */
function isEditorPage(pathname: string | null): boolean {
  if (!pathname) return false;
  return (
    pathname.startsWith('/admin/knowledge/new') ||
    /\/admin\/knowledge\/[^/]+\/edit$/.test(pathname) ||
    pathname.startsWith('/admin/posts/new') ||
    /\/admin\/posts\/[^/]+\/edit$/.test(pathname)
  );
}

/**
 * Admin layout — flat surface (no grid) to favour dense data work.
 * 1px line work, mono labels, zero radius.
 *
 * 鉴权：middleware 仅校验 cookie 存在；layout 内 useMe() 校验 JWT 有效性。
 * 失败时 request 拦截器会跳转 /login，避免页面继续渲染。
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { message } = App.useApp();
  const siteName = (process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev').toUpperCase();

  // 从 localStorage 恢复侧边栏折叠状态（避免 SSR/CSR hydration mismatch）
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem('admin:sidebar-collapsed');
      if (stored === '1') setCollapsed(true);
    } catch {
      // ignore
    }
    setHydrated(true);
  }, []);

  // 持久化折叠状态
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem('admin:sidebar-collapsed', collapsed ? '1' : '0');
    } catch {
      // ignore
    }
  }, [collapsed, hydrated]);

  // 校验当前博主身份：失败时由下方 useEffect 跳 /login
  // request 拦截器对 /auth/me 的 401 不立即跳转，给 React Query retry 一次容错；
  // 重试仍失败 → useMe 进入 isError → useEffect 触发跳转。
  const { data: me, isLoading, isError } = useMe();
  const logout = useLogout({
    onSuccess: () => {
      message.success('已退出登录');
      router.replace('/login');
      router.refresh();
    },
  });

  // useMe 重试后仍失败（会话失效/未登录）→ 跳登录页
  useEffect(() => {
    if (isError && typeof window !== 'undefined') {
      const { pathname, search } = window.location;
      if (!pathname.startsWith('/login')) {
        const redirect = encodeURIComponent(pathname + search);
        window.location.href = `/login?redirect=${redirect}`;
      }
    }
  }, [isError]);

  const editorPage = isEditorPage(pathname);

  const SidebarContent = (
    <>
      <div
        className={cn(
          'h-16 flex items-center border-b border-outline-variant',
          collapsed ? 'justify-center px-2' : 'justify-between px-5',
        )}
      >
        {collapsed ? (
          <button
            type="button"
            onClick={() => setCollapsed(false)}
            aria-label="展开侧边栏"
            title="展开侧边栏"
            className="text-on-surface-variant hover:text-primary transition-colors"
          >
            <PanelLeftOpen size={16} />
          </button>
        ) : (
          <>
            <Link
              href="/"
              className="font-mono text-label-mono text-primary uppercase tracking-widest font-semibold truncate"
            >
              {siteName} · ADMIN
            </Link>
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              aria-label="收起侧边栏"
              title="收起侧边栏"
              className="text-on-surface-variant hover:text-primary transition-colors shrink-0"
            >
              <PanelLeftClose size={16} />
            </button>
          </>
        )}
      </div>
      <nav className={cn('space-y-1 flex-1', collapsed ? 'p-2' : 'p-3')}>
        {menu.map((m) => {
          const active = pathname === m.href;
          return (
            <Link
              key={m.href}
              href={m.href}
              onClick={() => setOpen(false)}
              title={collapsed ? m.label : undefined}
              className={cn(
                'flex items-center transition-colors font-mono text-label-mono uppercase tracking-wider',
                collapsed
                  ? 'justify-center px-2 py-2'
                  : 'gap-3 px-3 py-2 text-body-sm',
                active
                  ? 'bg-primary text-on-primary'
                  : 'text-on-surface-variant hover:text-primary hover:bg-surface-container-lowest',
              )}
            >
              <m.icon size={16} className="shrink-0" />
              {!collapsed && <span>{m.label}</span>}
            </Link>
          );
        })}
      </nav>
      <div className={cn('border-t border-outline-variant', collapsed ? 'p-2' : 'p-3')}>
        <div
          className={cn(
            'font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest truncate',
            collapsed ? 'px-1 py-1 text-center' : 'px-3 py-2 mb-1',
          )}
          title={!collapsed ? undefined : me?.username}
        >
          {collapsed ? (
            isLoading ? (
              <Loader2 size={12} className="animate-spin inline" />
            ) : (
              <span className="text-[10px]">
                {(me?.username || '?').slice(0, 2)}
              </span>
            )
          ) : isLoading ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 size={12} className="animate-spin" />
              <span>校验中</span>
            </span>
          ) : (
            <span title={me?.username}>{me?.username || '未登录'}</span>
          )}
        </div>
        <button
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          title={collapsed ? '退出' : undefined}
          className={cn(
            'flex items-center font-mono text-label-mono text-on-surface-variant hover:text-error uppercase tracking-wider transition-colors disabled:opacity-50',
            collapsed
              ? 'w-full justify-center px-2 py-2'
              : 'w-full gap-3 px-3 py-2 text-body-sm',
          )}
        >
          <LogOut size={16} className="shrink-0" />
          {!collapsed && <span>{logout.isPending ? '退出中' : '退出'}</span>}
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-background flex">
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden md:flex flex-col border-r border-outline-variant bg-black sticky top-0 h-screen transition-[width] duration-200',
          collapsed ? 'w-16' : 'w-60',
        )}
      >
        {SidebarContent}
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="md:hidden fixed inset-0 z-[1050] flex">
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => setOpen(false)}
          />
          <aside className="relative w-60 flex flex-col bg-black border-r border-outline-variant">
            <button
              className="absolute top-4 right-4 text-on-surface-variant"
              onClick={() => setOpen(false)}
              aria-label="关闭"
            >
              <X size={20} />
            </button>
            {SidebarContent}
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <header className="h-16 border-b border-outline-variant flex items-center px-margin-mobile md:hidden">
          <button
            onClick={() => setOpen(true)}
            className="p-2 text-on-surface-variant"
            aria-label="菜单"
          >
            <MenuIcon size={22} />
          </button>
          <span className="ml-3 font-mono text-label-mono text-primary uppercase tracking-widest">
            {siteName} · ADMIN
          </span>
        </header>
        <main
          className={cn(
            'flex-1 w-full',
            editorPage
              ? 'p-0 max-w-none'
              : 'p-4 sm:p-6 max-w-admin mx-auto',
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
