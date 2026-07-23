'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { Button, Skeleton, Empty } from 'antd';
import {
  FileText,
  MessageSquare,
  Database,
  Eye,
  RefreshCw,
  TrendingUp,
  Flame,
} from 'lucide-react';
import { useStatsOverview } from '@/hooks/useAdmin';
import type { StatsSummary } from '@/lib/api/admin';
import { formatDate } from '@/lib/utils';

// 看板顶部 4 个卡片配置
const SUMMARY_CARDS: {
  title: string;
  unit: string;
  icon: typeof FileText;
  key: keyof StatsSummary;
}[] = [
  { title: '文章数', unit: 'POSTS', icon: FileText, key: 'postCount' },
  { title: '问答次数', unit: 'QUERIES', icon: MessageSquare, key: 'questionCount' },
  { title: '知识库文档', unit: 'DOCS', icon: Database, key: 'knowledgeDocCount' },
  { title: '本月访问', unit: 'VIEWS', icon: Eye, key: 'monthlyViews' },
];

export default function AdminHomePage() {
  const { data, isLoading, isFetching, refetch, isError, error } =
    useStatsOverview();

  return (
    <div>
      {/* 标题区 + 刷新 */}
      <div className="flex items-start justify-between gap-4 mb-2">
        <div>
          <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
            数据看板
          </h1>
          <p className="font-mono text-label-mono text-on-surface-variant mt-2 uppercase tracking-widest">
            DASHBOARD · 站点运营概览
          </p>
        </div>
        <Button
          type="text"
          size="small"
          icon={<RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />}
          onClick={() => refetch()}
          disabled={isFetching}
          className="font-mono text-label-mono uppercase tracking-widest text-on-surface-variant"
        >
          刷新
        </Button>
      </div>

      {/* 错误提示 */}
      {isError && (
        <div className="mt-4 mb-6 border border-error/60 bg-error-container/30 px-4 py-3">
          <p className="font-mono text-label-mono text-error uppercase tracking-widest">
            加载失败：{(error as Error)?.message || '未知错误'}
          </p>
        </div>
      )}

      {/* 4 卡片指标 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 border border-outline-variant mt-4 mb-12">
        {SUMMARY_CARDS.map((c, i) => (
          <div
            key={c.key}
            className={`p-6 bg-surface-container-lowest flex flex-col gap-3 ${
              i !== SUMMARY_CARDS.length - 1
                ? 'border-b sm:border-b-0 sm:border-r border-outline-variant'
                : ''
            } ${i === 1 ? 'sm:border-b lg:border-b-0' : ''} ${
              i === 2 ? 'lg:border-b-0 sm:border-r' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
                {c.title}
              </span>
              <c.icon size={16} className="text-on-surface-variant" />
            </div>
            <div className="font-mono text-3xl text-primary tabular-nums">
              {isLoading ? (
                <Skeleton.Input active size="small" style={{ width: 80 }} />
              ) : (
                (data?.summary[c.key] ?? 0).toLocaleString()
              )}
            </div>
            <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
              {c.unit}
            </span>
          </div>
        ))}
      </div>

      {/* 7 天趋势 + 热门文章 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 mb-12">
        <TrendCard trend={data?.trend} isLoading={isLoading} />
        <TopArticlesCard articles={data?.topArticles ?? []} isLoading={isLoading} />
      </div>

      {/* 热门问题 + 最近问答 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
        <TopQuestionsCard questions={data?.topQuestions ?? []} isLoading={isLoading} />
        <RecentQuestionsCard
          questions={data?.recentQuestions ?? []}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

// ===== 7 天趋势（文章 / 问答，简版柱状） =====
function TrendCard({
  trend,
  isLoading,
}: {
  trend?: { posts: number[]; questions: number[] };
  isLoading: boolean;
}) {
  const days = useMemo(() => {
    const out: string[] = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      out.push(`${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`);
    }
    return out;
  }, []);

  const posts = trend?.posts ?? [];
  const questions = trend?.questions ?? [];
  const max = Math.max(1, ...posts, ...questions);

  return (
    <section className="border border-outline-variant bg-surface-container-lowest p-6 lg:border-r-0">
      <SectionHeader title="近 7 天趋势" sub="TREND" icon={TrendingUp} />
      {isLoading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : (
        <div className="flex items-end gap-2 h-40 mt-6">
          {days.map((d, i) => {
            const p = posts[i] ?? 0;
            const q = questions[i] ?? 0;
            return (
              <div key={d} className="flex-1 flex flex-col items-center gap-1">
                <div className="flex items-end gap-0.5 h-full w-full justify-center">
                  <div
                    className="w-3 bg-primary/80"
                    style={{ height: `${(p / max) * 100}%`, minHeight: p > 0 ? 4 : 0 }}
                    title={`文章 ${p}`}
                  />
                  <div
                    className="w-3 bg-secondary/60"
                    style={{ height: `${(q / max) * 100}%`, minHeight: q > 0 ? 4 : 0 }}
                    title={`问答 ${q}`}
                  />
                </div>
                <span className="font-mono text-label-mono text-tertiary-fixed tabular-nums">
                  {d}
                </span>
              </div>
            );
          })}
        </div>
      )}
      <div className="flex items-center gap-4 mt-4 font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 bg-primary/80" /> 文章
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 bg-secondary/60" /> 问答
        </span>
      </div>
    </section>
  );
}

// ===== 热门文章 Top 5（按引用次数）=====
function TopArticlesCard({
  articles,
  isLoading,
}: {
  articles: { slug: string; title: string; channelName: string | null; citationCount: number }[];
  isLoading: boolean;
}) {
  return (
    <section className="border border-outline-variant bg-surface-container-lowest p-6">
      <SectionHeader title="热门文章" sub="TOP ARTICLES" icon={Flame} />
      {isLoading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : articles.length === 0 ? (
        <EmptyText text="暂无引用数据" />
      ) : (
        <ul className="mt-4 divide-y divide-outline-variant">
          {articles.map((a, i) => (
            <li key={a.slug} className="py-2 flex items-center gap-3">
              <span className="font-mono text-label-mono text-tertiary-fixed w-6 tabular-nums">
                {String(i + 1).padStart(2, '0')}
              </span>
              <Link
                href={`/posts/${a.slug}`}
                className="flex-1 min-w-0 text-on-surface hover:text-primary truncate transition-colors"
                title={a.title}
              >
                {a.title}
              </Link>
              {a.channelName && (
                <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest hidden sm:inline">
                  {a.channelName}
                </span>
              )}
              <span className="font-mono text-label-mono text-primary tabular-nums">
                ×{a.citationCount}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ===== 热门问题 Top 5（按出现次数）=====
function TopQuestionsCard({
  questions,
  isLoading,
}: {
  questions: { content: string; count: number }[];
  isLoading: boolean;
}) {
  return (
    <section className="border border-outline-variant bg-surface-container-lowest p-6 lg:border-r-0">
      <SectionHeader title="热门问题" sub="TOP QUESTIONS" icon={MessageSquare} />
      {isLoading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : questions.length === 0 ? (
        <EmptyText text="暂无问答数据" />
      ) : (
        <ul className="mt-4 divide-y divide-outline-variant">
          {questions.map((q, i) => (
            <li key={i} className="py-2 flex items-start gap-3">
              <span className="font-mono text-label-mono text-tertiary-fixed w-6 tabular-nums mt-0.5">
                {String(i + 1).padStart(2, '0')}
              </span>
              <span
                className="flex-1 min-w-0 text-on-surface truncate"
                title={q.content}
              >
                {q.content}
              </span>
              <span className="font-mono text-label-mono text-primary tabular-nums shrink-0">
                ×{q.count}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ===== 最近 10 条问答会话 =====
function RecentQuestionsCard({
  questions,
  isLoading,
}: {
  questions: {
    sessionId: string;
    title: string | null;
    personaName: string | null;
    scopeType: string;
    scopeRef: string | null;
    firstQuestion: string | null;
    lastAnswerSnippet: string | null;
    messageCount: number;
    createdAt: string;
  }[];
  isLoading: boolean;
}) {
  return (
    <section className="border border-outline-variant bg-surface-container-lowest p-6">
      <SectionHeader title="最近问答" sub="RECENT SESSIONS" icon={FileText} />
      {isLoading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : questions.length === 0 ? (
        <EmptyText text="暂无问答会话" />
      ) : (
        <ul className="mt-4 divide-y divide-outline-variant">
          {questions.map((q) => (
            <li key={q.sessionId} className="py-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-mono text-label-mono text-primary uppercase tracking-widest truncate">
                  {q.personaName || '未指定角色'}
                </span>
                <span className="font-mono text-label-mono text-tertiary-fixed tabular-nums shrink-0">
                  {formatDate(q.createdAt)} · {q.messageCount} MSGS
                </span>
              </div>
              <div className="text-on-surface text-body-sm truncate mb-1" title={q.firstQuestion || ''}>
                {q.firstQuestion || '(无内容)'}
              </div>
              {q.lastAnswerSnippet && (
                <div
                  className="font-mono text-label-mono text-on-surface-variant truncate"
                  title={q.lastAnswerSnippet}
                >
                  → {q.lastAnswerSnippet}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ===== 内部小组件 =====
function SectionHeader({
  title,
  sub,
  icon: Icon,
}: {
  title: string;
  sub: string;
  icon: typeof FileText;
}) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
        {title}
      </h2>
      <div className="flex items-center gap-2 font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
        <Icon size={14} />
        <span>{sub}</span>
      </div>
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return (
    <div className="py-10">
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
            {text}
          </span>
        }
      />
    </div>
  );
}
