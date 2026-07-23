import Link from 'next/link';
import { ArrowRight, ArrowUpRight, Filter } from 'lucide-react';
import AskBox from '@/components/chat/AskBox';
import { fetchPosts, fetchChannels } from '@/lib/api';

const author = process.env.NEXT_PUBLIC_SITE_AUTHOR || '博主';
const siteName = process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev';

function dateStamp(iso: string) {
  const d = new Date(iso);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${mm}-${dd}`;
}

export default async function HomePage() {
  const [postsData, channels] = await Promise.all([
    fetchPosts({ size: 30 }),
    fetchChannels().catch(() => []),
  ]);
  const { items } = postsData;
  // 第一个频道作为"浏览全部文章"的入口(文章即知识库,按频道组织)
  const primaryChannel = channels[0];
  // 最新发布取前 3 篇，其余作为历史存档
  const latestPosts = items.slice(0, 3);
  const archivePosts = items.slice(3);

  return (
    <div className="spatial-grid">
      {/* Hero — edge-to-edge functional zone */}
      <section className="border-b border-outline-variant">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-24">
          <div className="relative z-10 max-w-4xl">
            <div className="font-mono text-label-mono text-tertiary-fixed uppercase mb-4 tracking-[0.2em] animate-pulse">
              知识库问答系统已激活
            </div>
            <h1 className="font-headline text-headline-lg-mobile md:text-headline-lg text-primary mb-8 leading-tight tracking-tighter">
              文章即知识库。
              <br />
              <span className="text-on-surface-variant">问我的 AI。</span>
            </h1>
            <p className="font-sans text-body-md text-on-surface-variant max-w-2xl mb-12">
              {author} 的个人博客 {siteName} —— 把文章当作知识库来维护，每一篇发布后自动进入 AI 的检索范围。基于我写过的内容回答你，并附上引用出处。
            </p>
            <div className="max-w-2xl">
              <AskBox />
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              {primaryChannel && (
                <Link
                  href={`/channel/${primaryChannel.slug}`}
                  className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest flex items-center gap-2 transition-colors"
                >
                  浏览全部文章
                  <ArrowRight size={14} />
                </Link>
              )}
              <span className="text-outline-variant">·</span>
              <Link
                href="/ask"
                className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest flex items-center gap-2 transition-colors"
              >
                直接问 AI
                <ArrowUpRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Latest articles — Feature Cards */}
      <section className="border-b border-outline-variant">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
                最新发布
              </h2>
              <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase">
                前沿研究与实践架构更新
              </p>
            </div>
            {primaryChannel && (
              <Link
                href={`/channel/${primaryChannel.slug}`}
                className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest hidden md:block"
              >
                查看全部 →
              </Link>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {latestPosts.map((p, i) => (
              <Link
                key={p.id}
                href={`/posts/${p.slug}`}
                className="hover-card group flex flex-col gap-6 border border-outline-variant bg-surface-container-lowest p-8 h-full"
              >
                <div className="flex justify-between items-start">
                  <span className="font-mono text-label-mono text-tertiary-fixed border border-tertiary-fixed/40 px-2 py-0.5 uppercase">
                    #{String(i + 1).padStart(2, '0')} · {p.channelName}
                  </span>
                  <ArrowUpRight
                    size={16}
                    className="text-on-surface-variant group-hover:text-primary transition-colors"
                  />
                </div>
                <div>
                  <h3 className="font-headline text-headline-md text-primary mb-2 leading-snug">
                    {p.title}
                  </h3>
                  <p className="font-sans text-body-sm text-on-surface-variant line-clamp-2">
                    {p.excerpt}
                  </p>
                </div>
                <div className="mt-auto pt-4 border-t border-outline-variant flex justify-between items-center">
                  <span className="font-mono text-label-mono text-on-surface-variant uppercase">
                    {dateStamp(p.publishedAt)}
                    {p.readingTime ? ` · ${p.readingTime}MIN` : ''}
                  </span>
                  <span className="font-mono text-label-mono text-on-surface-variant group-hover:text-primary uppercase">
                    阅读 →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Historical Archive — list separated by 1px lines */}
      <section className="border-b border-outline-variant">
        <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-24">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
                历史存档
              </h2>
              <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase">
                深度技术洞察与经验沉淀
              </p>
            </div>
            <button
              className="p-2 border border-outline-variant text-on-surface-variant hover:text-primary hover:border-primary transition-colors"
              aria-label="筛选"
            >
              <Filter size={16} />
            </button>
          </div>

          <div className="border border-outline-variant">
            {archivePosts.map((p, i) => (
              <Link
                key={p.id}
                href={`/posts/${p.slug}`}
                className={`group flex flex-col gap-4 p-8 hover:bg-surface-container-lowest transition-colors ${
                  i !== archivePosts.length - 1 ? 'border-b border-outline-variant' : ''
                }`}
              >
                <div className="flex flex-col gap-2">
                  <h3 className="font-headline text-2xl text-primary group-hover:text-tertiary-fixed-dim transition-colors leading-snug">
                    {p.title}
                  </h3>
                  <p className="font-sans text-body-sm text-on-surface-variant">
                    {p.excerpt}
                  </p>
                </div>
                <div className="flex items-center gap-4 font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
                  <span>{dateStamp(p.publishedAt)}</span>
                  <span className="w-1 h-1 bg-outline-variant" />
                  <span>{p.channelName}</span>
                  {p.readingTime ? (
                    <>
                      <span className="w-1 h-1 bg-outline-variant" />
                      <span>{p.readingTime}MIN</span>
                    </>
                  ) : null}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
