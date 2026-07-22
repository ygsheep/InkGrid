import type { TocItem } from '@/types';

/**
 * Table of Contents — right-rail sticky nav.
 * 1px left border, current section promoted to primary (white).
 */
export default function TableOfContents({ items }: { items: TocItem[] }) {
  if (!items?.length) return null;
  return (
    <nav className="sticky top-24">
      <p className="font-mono text-label-mono text-on-surface-variant mb-3 uppercase tracking-widest">
        目录 · INDEX
      </p>
      <ul className="space-y-2 text-body-sm border-l border-outline-variant">
        {items.map((item) => (
          <li
            key={item.id}
            style={{ paddingLeft: item.level > 2 ? 20 : 12 }}
          >
            <a
              href={`#${item.id}`}
              className="block -ml-px border-l border-transparent pl-3 text-on-surface-variant hover:text-primary hover:border-primary transition-colors font-mono text-label-mono uppercase tracking-wider"
            >
              {item.title}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
