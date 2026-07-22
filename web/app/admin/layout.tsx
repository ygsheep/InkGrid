'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
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
} from 'lucide-react';
import { cn } from '@/lib/utils';

const menu = [
  { href: '/admin', label: '看板', icon: LayoutDashboard },
  { href: '/admin/posts', label: '文章', icon: FileText },
  { href: '/admin/knowledge', label: '知识库', icon: BookOpen },
  { href: '/admin/channels', label: '频道', icon: Layers },
  { href: '/admin/persona', label: '人设', icon: Bot },
  { href: '/admin/policy-collector', label: '政策采集', icon: Database },
  { href: '/admin/settings', label: '设置', icon: Settings },
];

/**
 * Admin layout — flat surface (no grid) to favour dense data work.
 * 1px line work, mono labels, zero radius.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const siteName = (process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev').toUpperCase();

  const SidebarContent = (
    <>
      <div className="h-16 flex items-center px-5 border-b border-outline-variant">
        <Link
          href="/"
          className="font-mono text-label-mono text-primary uppercase tracking-widest font-semibold"
        >
          {siteName} · ADMIN
        </Link>
      </div>
      <nav className="p-3 space-y-1 flex-1">
        {menu.map((m) => {
          const active = pathname === m.href;
          return (
            <Link
              key={m.href}
              href={m.href}
              onClick={() => setOpen(false)}
              className={cn(
                'flex items-center gap-3 px-3 py-2 text-body-sm transition-colors font-mono text-label-mono uppercase tracking-wider',
                active
                  ? 'bg-primary text-on-primary'
                  : 'text-on-surface-variant hover:text-primary hover:bg-surface-container-lowest',
              )}
            >
              <m.icon size={16} />
              <span>{m.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-outline-variant">
        <Link
          href="/"
          className="flex items-center gap-3 px-3 py-2 text-body-sm font-mono text-label-mono text-on-surface-variant hover:text-error uppercase tracking-wider transition-colors"
        >
          <LogOut size={16} />
          <span>退出</span>
        </Link>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-background flex">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-60 flex-col border-r border-outline-variant bg-black sticky top-0 h-screen">
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
        <main className="flex-1 p-4 sm:p-6 w-full max-w-admin mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
