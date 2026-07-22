import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import type { ArticleSummary } from '@/types';

/**
 * Feature Card — 1px outline-variant border, label-mono metadata.
 * Cards are grid-aligned regions defined by 1px borders; the hover state
 * promotes the border to primary (white) instead of relying on drop shadow.
 */
export default function ArticleCard({ post }: { post: ArticleSummary }) {
  return (
    <Link
      href={`/posts/${post.slug}`}
      className="hover-card group flex flex-col gap-6 border border-outline-variant bg-surface-container-lowest p-8 h-full"
    >
      <div className="flex justify-between items-start">
        <span className="font-mono text-label-mono text-tertiary-fixed border border-tertiary-fixed/40 px-2 py-0.5 uppercase">
          #{post.channelName}
        </span>
        <ArrowUpRight
          size={16}
          className="text-on-surface-variant group-hover:text-primary transition-colors"
        />
      </div>
      <div>
        <h3 className="font-headline text-headline-md text-primary mb-2 leading-snug">
          {post.title}
        </h3>
        <p className="font-sans text-body-sm text-on-surface-variant line-clamp-2">
          {post.excerpt}
        </p>
      </div>
      <div className="mt-auto pt-4 border-t border-outline-variant flex justify-between items-center">
        <span className="font-mono text-label-mono text-on-surface-variant uppercase">
          {formatDate(post.publishedAt)}
          {post.readingTime ? ` · ${post.readingTime}MIN` : ''}
        </span>
        <span className="font-mono text-label-mono text-on-surface-variant group-hover:text-primary uppercase">
          阅读 →
        </span>
      </div>
    </Link>
  );
}
