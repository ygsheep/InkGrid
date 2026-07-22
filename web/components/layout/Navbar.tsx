'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Drawer } from 'antd';
import { Menu, Search, MessageSquare, Mic, User } from 'lucide-react';
import { cn } from '@/lib/utils';

const navLinks = [
  { href: '/', label: '首页' },
  { href: '/posts', label: '文章' },
  { href: '/channel/channel', label: '经验' },
  { href: '/channel/policy', label: '政策' },
  { href: '/ask/persona', label: 'AI 角色' },
  { href: '/about', label: '关于' },
];

const actions = [
  { href: '/search', icon: Search, label: '搜索' },
  { href: '/ask', icon: MessageSquare, label: '问 AI' },
  { href: '/ask/voice', icon: Mic, label: '语音' },
  { href: '/login', icon: User, label: '管理' },
];

/**
 * TopNavBar — fixed, full-width, 1px outline-variant bottom border.
 * Edge-to-edge functional zone, zero-radius, mono labels.
 */
export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const siteName = (process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev').toUpperCase();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={cn(
        'fixed top-0 inset-x-0 z-[1020] backdrop-blur-md transition-colors duration-200',
        'border-b border-outline-variant bg-black/80',
        scrolled && 'bg-black/95',
      )}
    >
      <nav className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop h-16 flex items-center justify-between">
        {/* Logo + desktop nav */}
        <div className="flex items-center gap-8 h-full">
          <Link
            href="/"
            className="font-mono text-label-mono font-bold tracking-widest text-primary uppercase h-full flex items-center"
          >
            {siteName}
          </Link>
          <div className="hidden md:flex gap-grid-major items-center h-full">
            {navLinks.map((l) => {
              const active = pathname === l.href;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={cn(
                    'font-mono text-label-mono uppercase tracking-widest h-full flex items-center border-b-2 -mb-px transition-colors duration-200',
                    active
                      ? 'text-primary border-primary'
                      : 'text-on-surface-variant hover:text-primary border-transparent',
                  )}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Right actions */}
        <div className="hidden md:flex items-center gap-4">
          {actions.map((a) => (
            <Link
              key={a.href}
              href={a.href}
              aria-label={a.label}
              className="p-2 text-on-surface-variant hover:text-primary transition-colors"
            >
              <a.icon size={18} />
            </Link>
          ))}
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 text-on-surface-variant hover:text-primary"
          onClick={() => setOpen(true)}
          aria-label="菜单"
        >
          <Menu size={22} />
        </button>
      </nav>

      {/* Mobile drawer */}
      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        placement="right"
        width={260}
        title={
          <span className="font-mono text-label-mono text-primary uppercase tracking-widest">
            {siteName}
          </span>
        }
        styles={{
          header: { borderBottomColor: '#1a1a1a', background: '#0a0a0a' },
          body: { padding: 0, background: '#0a0a0a' },
        }}
      >
        <div className="flex flex-col">
          {navLinks.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className={cn(
                'px-5 py-4 font-mono text-label-mono border-b border-outline-variant uppercase tracking-widest',
                pathname === l.href ? 'text-primary bg-surface-container-lowest' : 'text-on-surface-variant',
              )}
            >
              {l.label}
            </Link>
          ))}
          <div className="flex justify-around px-5 py-6">
            {actions.map((a) => (
              <Link
                key={a.href}
                href={a.href}
                onClick={() => setOpen(false)}
                aria-label={a.label}
                className="p-3 text-on-surface-variant hover:text-primary border border-outline-variant"
              >
                <a.icon size={18} />
              </Link>
            ))}
          </div>
        </div>
      </Drawer>
    </header>
  );
}
