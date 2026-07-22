import ArticleCard from '@/components/blog/ArticleCard';
import { fetchPosts } from '@/lib/api';

export const metadata = { title: '文章' };

export default async function PostsPage() {
  const { items, total } = await fetchPosts({ size: 100 });
  return (
    <div className="spatial-grid">
      <section className="border-b border-outline-variant">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
                全部文章
              </h1>
              <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase">
                共 {total} 篇 · ARCHIVE
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((p) => (
              <ArticleCard key={p.id} post={p} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
