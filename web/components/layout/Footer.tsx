import Link from 'next/link';

/**
 * Footer — edge-to-edge functional zone divided by 1px outline-variant border.
 * Mono labels for metadata, no decorative imagery.
 */
export default function Footer() {
  const year = new Date().getFullYear();
  const siteName = (process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev').toUpperCase();
  const author = process.env.NEXT_PUBLIC_SITE_AUTHOR || '博主';
  const version = (process.env.NEXT_PUBLIC_SITE_VERSION || 'v0.0.0').toUpperCase();

  return (
    <footer className="border-t border-outline-variant mt-0">
      <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major grid grid-cols-1 md:grid-cols-2 gap-grid-major">
        <div className="flex flex-col gap-3">
          <p className="font-mono text-label-mono text-primary uppercase tracking-widest">
            {siteName}
          </p>
          <p className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
            © {year} {author}
          </p>
          <p className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
            存档版本: {version}
          </p>
        </div>
        <div className="flex flex-col gap-3 md:items-end md:text-right">
          <Link
            href="/ask"
            className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest transition-colors"
          >
            问 AI
          </Link>
          <Link
            href="/search"
            className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest transition-colors"
          >
            搜索
          </Link>
          <Link
            href="/login"
            className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest transition-colors"
          >
            管理
          </Link>
          <p className="font-mono text-label-mono text-primary uppercase tracking-widest mt-2">
            全程端到端加密
          </p>
        </div>
      </div>
    </footer>
  );
}
