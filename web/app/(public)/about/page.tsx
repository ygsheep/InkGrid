export const metadata = { title: '关于' };

export default function AboutPage() {
  const author = process.env.NEXT_PUBLIC_SITE_AUTHOR || '张三';
  const siteName = process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev';

  return (
    <div className="border-b border-outline-variant">
      <section className="mx-auto max-w-article px-margin-mobile md:px-margin-desktop py-grid-major">
        <h1 className="font-headline text-headline-lg-mobile md:text-headline-lg text-primary leading-tight tracking-tighter">
          关于
        </h1>
        <p className="font-mono text-label-mono text-on-surface-variant mt-4 mb-12 uppercase tracking-widest">
          ABOUT · {siteName.toUpperCase()}
        </p>

        <div className="article-content">
          <p>
            这里是 {author} 的个人博客 {siteName}。
          </p>
          <p>
            我把文章当作知识库来维护——每一篇发布后都会自动进入 AI 的检索范围。你可以随时向 AI 提问，它会基于我写过的内容回答你，并附上引用出处。
          </p>
          <blockquote>
            读 → 问 → 读：从一篇文章出发提问，再回到原文深入。
          </blockquote>
          <p>技术栈：Next.js 14 + FastAPI + Milvus + 国产 LLM。</p>
        </div>
      </section>
    </div>
  );
}
