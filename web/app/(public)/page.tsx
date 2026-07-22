import Link from 'next/link';
import { ArrowRight, ArrowUpRight, Filter } from 'lucide-react';
import AskBox from '@/components/chat/AskBox';
import type { ArticleSummary } from '@/types';

const author = process.env.NEXT_PUBLIC_SITE_AUTHOR || '博主';
const siteName = process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev';

// 骨架阶段 mock 数据，接后端后替换为 fetch + SSG
const latestPosts: ArticleSummary[] = [
  {
    id: '1',
    slug: 'candidate-eval',
    title: '候选人评估三维度',
    excerpt: '定义下一代评估框架：技术深度、协作能力、成长潜力的语义握手与坐标对齐。',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-20',
    readingTime: 8,
  },
  {
    id: '2',
    slug: 'shenzhen-talent-subsidy',
    title: '深圳人才补贴指南',
    excerpt: '在毫米级响应需求下，构建高弹性的政策申请流程与新引进人才补贴节点。',
    channel: 'policy',
    channelName: '政策',
    publishedAt: '2026-07-18',
    readingTime: 6,
  },
  {
    id: '3',
    slug: 'rag-architecture',
    title: '我的 RAG 架构选型',
    excerpt: '量化 RAG 架构中向量索引算法对基础检索召回率与精度的结构性影响。',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-15',
    readingTime: 12,
  },
];

const archivePosts: ArticleSummary[] = [
  {
    id: '4',
    slug: 'remote-work',
    title: '远程办公实践',
    excerpt: '我倾向于异步沟通，这是三年远程协作的总结。',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-10',
    readingTime: 10,
  },
  {
    id: '5',
    slug: 'interview-questions',
    title: '面试我会问的问题',
    excerpt: '三个维度评估一个人，技术只是其中之一。',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-08',
    readingTime: 5,
  },
  {
    id: '6',
    slug: 'shenzhen-rent-policy',
    title: '深圳公租房申请条件',
    excerpt: '户籍、社保、收入三道门槛，2026 年最新标准。',
    channel: 'policy',
    channelName: '政策',
    publishedAt: '2026-07-05',
    readingTime: 7,
  },
];

function dateStamp(iso: string) {
  const d = new Date(iso);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${mm}-${dd}`;
}

export default function HomePage() {
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
              <Link
                href="/posts"
                className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest flex items-center gap-2 transition-colors"
              >
                浏览全部文章
                <ArrowRight size={14} />
              </Link>
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
            <Link
              href="/posts"
              className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest hidden md:block"
            >
              查看全部 →
            </Link>
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
