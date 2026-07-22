import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import ArticleShell from '@/components/blog/ArticleShell';
import { fetchPost, fetchChannelPosts } from '@/lib/api';

export async function generateStaticParams() {
  // 不预生成 slug，按需 SSR/ISR
  return [];
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  try {
    const a = await fetchPost(params.slug);
    return { title: a.title };
  } catch {
    return { title: '文章' };
  }
}

export default async function ArticlePage({
  params,
}: {
  params: { slug: string };
}) {
  let article;
  try {
    article = await fetchPost(params.slug);
  } catch {
    notFound();
  }

  // 相关归档：同频道其他文章（排除当前）
  let relatedPosts: { slug: string; title: string; publishedAt: string }[] = [];
  try {
    const channelPosts = await fetchChannelPosts(article!.channel);
    relatedPosts = channelPosts
      .filter((p) => p.slug !== params.slug)
      .slice(0, 3)
      .map((p) => ({
        slug: p.slug,
        title: p.title,
        publishedAt: p.publishedAt,
      }));
  } catch {
    /* 相关文章获取失败不影响主渲染 */
  }

  return (
    <ArticleShell
      slug={params.slug}
      article={article!}
      relatedPosts={relatedPosts}
    />
  );
}
