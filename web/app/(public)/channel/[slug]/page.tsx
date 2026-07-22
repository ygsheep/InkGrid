import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import AskBox from '@/components/chat/AskBox';
import ArticleCard from '@/components/blog/ArticleCard';
import { fetchChannel, fetchChannelPosts, fetchChannels } from '@/lib/api';

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
}: {
  params: { slug: string };
}) {
  let channel;
  try {
    channel = await fetchChannel(params.slug);
  } catch {
    notFound();
  }
  const posts = await fetchChannelPosts(params.slug);
  // Channel identity is now expressed via 1px stroke + label-mono, not hue.
  const accent = channel!.accent === 'policy' ? 'tertiary-fixed' : 'primary';

  return (
    <div className="spatial-grid">
      {/* Channel header — 1px bordered zone */}
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

      {/* Channel articles */}
      <section className="border-b border-outline-variant">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
                频道文章
              </h2>
              <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase">
                共 {posts.length} 篇 · {channel!.name.toUpperCase()}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {posts.map((p) => (
              <ArticleCard key={p.id} post={p} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
