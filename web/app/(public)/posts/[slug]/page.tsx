import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import ArticleShell from '@/components/blog/ArticleShell';
import MarkdownContent from '@/components/blog/MarkdownContent';
import { extractToc } from '@/lib/markdown/extractToc';
import { fetchPost, fetchChannelPosts, fetchAdjacentPosts } from '@/lib/api';

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
    const description = a.excerpt || a.content?.slice(0, 160) || '';
    return {
      title: a.title,
      description,
      openGraph: {
        title: a.title,
        description,
        type: 'article',
        publishedTime: a.publishedAt,
        tags: a.tags,
      },
    };
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
    const { items: channelPosts } = await fetchChannelPosts(article!.channel);
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

  // 上一篇 / 下一篇：相邻文章（按发布时间）
  let adjacentPosts:
    | {
        prev: { slug: string; title: string; publishedAt: string } | null;
        next: { slug: string; title: string; publishedAt: string } | null;
      }
    | undefined;
  try {
    const adj = await fetchAdjacentPosts(params.slug);
    adjacentPosts = {
      prev: adj.prev
        ? {
            slug: adj.prev.slug,
            title: adj.prev.title,
            publishedAt: adj.prev.publishedAt,
          }
        : null,
      next: adj.next
        ? {
            slug: adj.next.slug,
            title: adj.next.title,
            publishedAt: adj.next.publishedAt,
          }
        : null,
    };
  } catch {
    /* 邻接文章获取失败不影响主渲染 */
  }

  return (
    <ArticleShell
      slug={params.slug}
      article={{ ...article!, toc: article!.toc?.length ? article!.toc : extractToc(article!.content) }}
      relatedPosts={relatedPosts}
      adjacentPosts={adjacentPosts}
    >
      <MarkdownContent source={article!.content} />
    </ArticleShell>
  );
}
