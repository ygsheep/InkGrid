import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { X } from 'lucide-react';
import AskBox from '@/components/chat/AskBox';
import ArticleCard from '@/components/blog/ArticleCard';
import {
  fetchChannel,
  fetchChannelPosts,
  fetchChannelTags,
  fetchChannels,
} from '@/lib/api';

export async function generateStaticParams() {
  try {
    const channels = await fetchChannels();
    return channels.map((c) => ({ slug: c.slug }));
  } catch {
    return [];
  }
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  try {
    const c = await fetchChannel(params.slug);
    return { title: c.name };
  } catch {
    return { title: '频道' };
  }
}

export default async function ChannelPage({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams: { tag?: string };
}) {
  let channel;
  try {
    channel = await fetchChannel(params.slug);
  } catch {
    notFound();
  }

  // 并行拉取:所有频道(切换)、当前频道标签(筛选)、当前频道文章(含标签筛选)
  const [allChannels, tagsData, postsData] = await Promise.all([
    fetchChannels().catch(() => []),
    fetchChannelTags(params.slug).catch(() => ({ items: [], total: 0 })),
    fetchChannelPosts(params.slug, { tag: searchParams.tag, size: 100 }),
  ]);

  const posts = postsData.items;
  const tags = tagsData.items;
  const activeTag = searchParams.tag;
  const accent = channel!.accent === 'policy' ? 'tertiary-fixed' : 'primary';

  return (
    <div className="spatial-grid">
      {/* Channel header */}
      <section className="border-b border-outline-variant">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
          <div className="border border-outline-variant p-8 md:p-12">
            <span
              className={`font-mono text-label-mono uppercase tracking-widest ${
                accent === 'tertiary-fixed' ? 'text-tertiary-fixed' : 'text-primary'
              }`}
            >
              ◆ {channel!.name}
            </span>
            <h1 className="font-headline text-headline-lg-mobile md:text-headline-lg text-primary mt-4 leading-tight tracking-tighter">
              {channel!.name}
            </h1>
            <p className="font-sans text-body-md text-on-surface-variant mt-4 max-w-2xl">
              {channel!.description}
            </p>
            <div className="mt-8 max-w-2xl">
              <AskBox
                scope={channel!.slug}
                placeholder={`向 AI 提问（${channel!.name}）…`}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Filters: channel switch + tag filter */}
      <section className="border-b border-outline-variant sticky top-16 z-30 bg-surface-container-lowest backdrop-blur-md">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-5">
          {/* Channel switcher — tab style, mirrors top navbar */}
          {allChannels.length > 1 && (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mr-3">
                频道
              </span>
              {allChannels.map((c) => {
                const active = c.slug === params.slug;
                return (
                  <Link
                    key={c.slug}
                    href={`/channel/${c.slug}`}
                    className={`font-mono text-label-mono uppercase tracking-widest px-2 py-1 border-b-2 -mb-px transition-colors ${
                      active
                        ? 'border-primary text-primary'
                        : 'border-transparent text-on-surface-variant hover:text-primary hover:border-primary/50'
                    }`}
                  >
                    {c.name}
                  </Link>
                );
              })}
            </div>
          )}

          {/* Tag filter — chip style, separated by divider */}
          {tags.length > 0 && (
            <div
              className={`flex items-center gap-2 flex-wrap pt-4 border-t border-outline-variant/50 ${
                allChannels.length > 1 ? 'mt-4' : ''
              }`}
            >
              <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest mr-2">
                标签
              </span>
              {tags.map((t) => {
                const active = activeTag === t.tag;
                return (
                  <Link
                    key={t.tag}
                    href={`/channel/${params.slug}?tag=${encodeURIComponent(t.tag)}`}
                    className={`font-mono text-label-mono uppercase tracking-widest px-3 py-1 border transition-colors ${
                      active
                        ? 'border-primary text-primary'
                        : 'border-outline-variant text-on-surface-variant hover:text-primary hover:border-primary'
                    }`}
                  >
                    {t.tag} · {t.count}
                  </Link>
                );
              })}
              {activeTag && (
                <Link
                  href={`/channel/${params.slug}`}
                  className="font-mono text-label-mono uppercase tracking-widest px-2 py-1 text-tertiary-fixed hover:text-primary flex items-center gap-1 transition-colors"
                >
                  <X size={12} />
                  清除
                </Link>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Channel articles */}
      <section className="border-b border-outline-variant relative">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
                {activeTag ? `#${activeTag}` : '频道文章'}
              </h2>
              <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase">
                共 {posts.length} 篇 · {channel!.name.toUpperCase()}
                {activeTag ? ` · TAG ${activeTag.toUpperCase()}` : ''}
              </p>
            </div>
          </div>
          {posts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {posts.map((p) => (
                <ArticleCard key={p.id} post={p} />
              ))}
            </div>
          ) : (
            <div className="border border-outline-variant p-16 text-center">
              <p className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                {activeTag ? `此标签下暂无文章` : `暂无文章`}
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
