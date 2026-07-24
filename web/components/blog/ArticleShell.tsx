'use client';

import { ReactNode, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Network, History, FlipHorizontal } from 'lucide-react';
import AskBox from '@/components/chat/AskBox';
import TableOfContents from '@/components/blog/TableOfContents';
import { formatDate } from '@/lib/utils';
import type { Article } from '@/types';

export interface RelatedPost {
  slug: string;
  title: string;
  publishedAt: string;
}

interface ArticleShellProps {
  slug: string;
  article: Article;
  /** 由 server component 渲染好的 markdown 内容 */
  children?: ReactNode;
  /** 相关归档文章（可选，page 通过 fetchChannelPosts 等方式获取） */
  relatedPosts?: RelatedPost[];
  /** 上一篇 / 下一篇导航（可选，page 通过 fetchAdjacentPosts 获取） */
  adjacentPosts?: {
    prev: { slug: string; title: string; publishedAt: string } | null;
    next: { slug: string; title: string; publishedAt: string } | null;
  };
}

/**
 * ArticleShell — 文章详情布局壳。
 *
 * 顶部 meta 行右侧提供"切换侧栏"按钮，可在左右之间切换侧边栏位置；
 * 偏好持久化到 localStorage（key: article-sidebar-position）。
 *
 * 侧边栏包含三段 widget，按上到下排列：
 *   1. 目录（TableOfContents）
 *   2. 核心概念实体（标签芯片集合）
 *   3. 相关归档文章（日期 + 标题列表）
 *
 * 移动端侧边栏隐藏（hidden lg:block），切换按钮也仅在 lg+ 显示。
 */
const STORAGE_KEY = 'article-sidebar-position';

export default function ArticleShell({ slug, article, relatedPosts = [], adjacentPosts, children }: ArticleShellProps) {
  const [sidebarLeft, setSidebarLeft] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // 读取持久化偏好
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'left') setSidebarLeft(true);
    else if (saved === 'right') setSidebarLeft(false);
    setHydrated(true);
  }, []);

  const toggleSidebar = () => {
    const next = !sidebarLeft;
    setSidebarLeft(next);
    localStorage.setItem(STORAGE_KEY, next ? 'left' : 'right');
  };

  const a = article;
  const concepts = a.tags ?? [];
  const readingTimeLabel = a.readingTime ? `${a.readingTime} MIN READ` : 'MIN READ';

  return (
    <article className="border-b border-outline-variant">
      <div className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
        {/* 顶部 meta 行：返回链接 + 侧栏切换按钮 */}
        <div className="flex justify-between items-center gap-4">
          <Link
            href={`/channel?channel=${a.channel}`}
            className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest flex items-center gap-2"
          >
            <ArrowLeft size={12} />
            {a.channelName}
          </Link>
          <button
            onClick={toggleSidebar}
            aria-label="切换侧边栏位置"
            className="hidden lg:flex font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest items-center gap-2 border border-outline-variant px-3 py-1.5 transition-colors hover:border-primary"
          >
            <FlipHorizontal size={12} />
            切换侧栏
            <span className="text-tertiary-fixed">
              {hydrated ? (sidebarLeft ? '← 左' : '→ 右') : ''}
            </span>
          </button>
        </div>

        <div className="flex flex-col lg:flex-row gap-10 mt-8">
          {/* 文章主体 */}
          <div
            className={`max-w-article w-full lg:flex-1 ${
              hydrated && sidebarLeft ? 'lg:order-2' : 'lg:order-1'
            }`}
          >
            <h1 className="font-headline text-headline-lg-mobile md:text-headline-lg text-primary leading-tight tracking-tighter">
              {a.title}
            </h1>
            <div className="mt-6 flex flex-wrap items-center gap-4 font-mono text-label-mono text-on-surface-variant uppercase tracking-widest border-b border-outline-variant pb-6">
              <span>{formatDate(a.publishedAt)}</span>
              <span className="w-1 h-1 bg-outline-variant" />
              <span>{a.channelName}</span>
              <span className="w-1 h-1 bg-outline-variant" />
              <span>{readingTimeLabel}</span>
            </div>

            <div className="article-content mt-10">
              {children}
            </div>

            {/* 上一篇 / 下一篇导航 */}
            {adjacentPosts && (adjacentPosts.prev || adjacentPosts.next) && (
              <nav
                aria-label="上一篇 / 下一篇"
                className="mt-16 border-t border-outline-variant pt-8"
              >
                <p className="font-mono text-label-mono text-on-surface-variant mb-4 uppercase tracking-widest">
                  CONTINUE READING
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* 上一篇 */}
                  <div className="min-h-[5rem]">
                    {adjacentPosts.prev ? (
                      <Link
                        href={`/posts/${adjacentPosts.prev.slug}`}
                        className="group flex flex-col gap-2 border border-outline-variant p-5 h-full transition-colors hover:border-primary"
                      >
                        <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest flex items-center gap-1.5">
                          <ArrowLeft size={12} />
                          上一篇 · PREV
                        </span>
                        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                          {formatDate(adjacentPosts.prev.publishedAt)}
                        </span>
                        <span className="font-sans text-body-sm text-on-surface group-hover:text-primary transition-colors leading-tight">
                          {adjacentPosts.prev.title}
                        </span>
                      </Link>
                    ) : (
                      <div className="border border-outline-variant p-5 h-full opacity-40">
                        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                          上一篇 · PREV
                        </span>
                      </div>
                    )}
                  </div>

                  {/* 下一篇 */}
                  <div className="min-h-[5rem]">
                    {adjacentPosts.next ? (
                      <Link
                        href={`/posts/${adjacentPosts.next.slug}`}
                        className="group flex flex-col gap-2 border border-outline-variant p-5 h-full text-right transition-colors hover:border-primary"
                      >
                        <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest flex items-center justify-end gap-1.5">
                          下一篇 · NEXT
                          <ArrowRight size={12} />
                        </span>
                        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                          {formatDate(adjacentPosts.next.publishedAt)}
                        </span>
                        <span className="font-sans text-body-sm text-on-surface group-hover:text-primary transition-colors leading-tight">
                          {adjacentPosts.next.title}
                        </span>
                      </Link>
                    ) : (
                      <div className="border border-outline-variant p-5 h-full text-right opacity-40">
                        <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
                          下一篇 · NEXT
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </nav>
            )}

            {/* 文末问 AI */}
            <div className="mt-16 border-t border-outline-variant pt-8">
              <p className="font-mono text-label-mono text-on-surface-variant mb-4 uppercase tracking-widest">
                关于本文还想问？基于这篇文章向 AI 深入提问
              </p>
              <AskBox scope={`article:${slug}`} placeholder="基于本文提问…" />
            </div>
          </div>

          {/* 侧边栏：目录 + 核心概念 + 相关归档 */}
          <aside
            className={`hidden lg:block lg:w-[240px] lg:shrink-0 ${
              hydrated && sidebarLeft ? 'lg:order-1' : 'lg:order-2'
            }`}
          >
            <div className="sticky top-24 space-y-8">
              <TableOfContents items={a.toc ?? []} />

              {/* 核心概念实体 */}
              {concepts.length > 0 && (
                <section className="border border-outline-variant bg-surface-container-lowest/60 p-6 space-y-4">
                  <h3 className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                    <Network size={12} className="text-tertiary-fixed" />
                    核心概念实体
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {concepts.map((c) => (
                      <span
                        key={c}
                        className="bg-surface-container-high px-2 py-1 font-mono text-label-mono text-on-surface-variant uppercase border border-outline-variant hover:border-primary hover:text-primary cursor-pointer transition-all tracking-wider"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* 相关归档文章 */}
              {relatedPosts.length > 0 && (
                <section className="border border-outline-variant bg-surface-container-lowest/60 p-6 space-y-6">
                  <h3 className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest flex items-center gap-2">
                    <History size={12} className="text-tertiary-fixed" />
                    相关归档文章
                  </h3>
                  <div className="space-y-5">
                    {relatedPosts.map((r) => (
                      <Link
                        key={r.slug}
                        href={`/posts/${r.slug}`}
                        className="group block"
                      >
                        <div className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest mb-1">
                          {formatDate(r.publishedAt)}
                        </div>
                        <div className="font-sans text-body-sm text-on-surface group-hover:text-primary transition-colors leading-tight">
                          {r.title}
                        </div>
                      </Link>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </aside>
        </div>
      </div>
    </article>
  );
}
