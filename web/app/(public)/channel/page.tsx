import Link from 'next/link';
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

export const metadata: Metadata = { title: '频道' };

/**
 * 频道单页 —— 所有频道聚合在一个页面,通过横向 chips 切换频道,不进行页面跳转。
 *
 * URL 约定:
 *  - /channel                       → 默认取第一个频道
 *  - /channel?channel=xxx           → 指定频道
 *  - /channel?channel=xxx&tag=yyy   → 指定频道 + 标签筛选
 *
 * 切换频道时清空 tag(标签是频道维度的);切换通过 query param 更新,RSC 重渲染,
 * 不触发路由跳转,保持页面布局稳定。
 */
export default async function ChannelPage({
  searchParams,
}: {
  searchParams: { channel?: string; tag?: string };
}) {
  const allChannels = await fetchChannels().catch(() => []);

  // 确定当前频道:优先 searchParams.channel,否则取第一个频道
  const requestedSlug = searchParams.channel;
  const activeSlug =
    requestedSlug && allChannels.some((c) => c.slug === requestedSlug)
      ? requestedSlug
      : allChannels[0]?.slug;

  // 无频道数据时展示空状态
  if (!activeSlug || allChannels.length === 0) {
    return (
      <div className="spatial-grid">
        <section className="border-b border-outline-variant">
          <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
            <div className="border border-outline-variant p-16 text-center">
              <p className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                暂无频道
              </p>
            </div>
          </div>
        </section>
      </div>
    );
  }

  // 并行拉取:当前频道详情、当前频道标签、当前频道文章(含标签筛选)
  const [channel, tagsData, postsData] = await Promise.all([
    fetchChannel(activeSlug).catch(() => null),
    fetchChannelTags(activeSlug).catch(() => ({ items: [], total: 0 })),
    fetchChannelPosts(activeSlug, { tag: searchParams.tag, size: 100 }),
  ]);

  const posts = postsData.items;
  const tags = tagsData.items;
  const activeTag = searchParams.tag;
  const accent = channel?.accent === 'policy' ? 'tertiary-fixed' : 'primary';

  return (
    <div className="spatial-grid">
      {/* Channel header —— 随当前频道变化 */}
      <section className="border-b border-outline-variant">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
          <div className="border border-outline-variant p-8 md:p-12">
            <span
              className={`font-mono text-label-mono uppercase tracking-widest ${
                accent === 'tertiary-fixed' ? 'text-tertiary-fixed' : 'text-primary'
              }`}
            >
              ◆ {channel?.name ?? activeSlug}
            </span>
            <h1 className="font-headline text-headline-lg-mobile md:text-headline-lg text-primary mt-4 leading-tight tracking-tighter">
              {channel?.name ?? activeSlug}
            </h1>
            {channel?.description && (
              <p className="font-sans text-body-md text-on-surface-variant mt-4 max-w-2xl">
                {channel.description}
              </p>
            )}
            <div className="mt-8 max-w-2xl">
              <AskBox
                scope={activeSlug}
                placeholder={`向 AI 提问（${channel?.name ?? activeSlug}）…`}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Filters:频道 chips + 标签 chips,sticky 吸顶 */}
      <section className="border-b border-outline-variant sticky top-16 z-30 bg-black">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-5">
          {/* 频道切换 —— 横向 chips */}
          <div className="flex items-center gap-1 flex-wrap">
            <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mr-3">
              频道
            </span>
            {allChannels.map((c) => {
              const active = c.slug === activeSlug;
              return (
                <Link
                  key={c.slug}
                  href={`/channel?channel=${encodeURIComponent(c.slug)}`}
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

          {/* 标签筛选 —— chip style,与频道切换用分隔线区分 */}
          {tags.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap pt-4 mt-4 border-t border-outline-variant/50">
              <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest mr-2">
                标签
              </span>
              {tags.map((t) => {
                const active = activeTag === t.tag;
                return (
                  <Link
                    key={t.tag}
                    href={`/channel?channel=${encodeURIComponent(activeSlug)}&tag=${encodeURIComponent(t.tag)}`}
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
                  href={`/channel?channel=${encodeURIComponent(activeSlug)}`}
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

      {/* 频道文章列表 */}
      <section className="border-b border-outline-variant relative isolate">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
                {activeTag ? `#${activeTag}` : '频道文章'}
              </h2>
              <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase">
                共 {posts.length} 篇 · {(channel?.name ?? activeSlug).toUpperCase()}
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
