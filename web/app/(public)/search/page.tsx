'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Search as SearchIcon, Loader2, Flame, Clock } from 'lucide-react';
import {
  useSearch,
  useSearchSuggestions,
  addSearchHistory,
  getSearchHistory,
  clearSearchHistory,
} from '@/hooks/useSearch';
import { useChannels } from '@/hooks/useChannels';
import { cn } from '@/lib/utils';

/** unix timestamp → YYYY-MM-DD */
function tsToDate(ts: number): string {
  if (!ts) return '';
  const d = new Date(ts * 1000);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [channel, setChannel] = useState<string>('');
  const [focused, setFocused] = useState(false);
  const [history, setHistory] = useState<string[]>([]);

  const { data: channels = [] } = useChannels();
  const { data: suggestions } = useSearchSuggestions(5);

  const { data, isLoading, isFetching } = useSearch(q, {
    limit: 20,
    channel: channel || undefined,
  });

  const hasQuery = q.trim().length > 0;
  const showPanel = focused && !hasQuery;

  // 聚焦时刷新历史
  useEffect(() => {
    if (focused) setHistory(getSearchHistory());
  }, [focused]);

  const doSearch = (term: string) => {
    setQ(term);
    if (term.trim()) {
      addSearchHistory(term.trim());
      setHistory(getSearchHistory());
    }
  };

  const hits = data?.hits ?? [];
  const total = data?.estimatedTotalHits ?? 0;
  const suggestionList = suggestions?.suggestions ?? [];

  return (
    <div className="border-b border-outline-variant">
      <section className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
        <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter mb-2">
          搜索
        </h1>
        <p className="font-mono text-label-mono text-on-surface-variant mb-12 uppercase">
          SEARCH · 全站文章索引
        </p>

        {/* 搜索框 + 建议/历史面板 */}
        <div className="relative">
          <div className="flex border border-outline-variant focus-within:border-primary transition-colors">
            <span className="flex items-center pl-4 text-on-surface-variant">
              <SearchIcon size={16} />
            </span>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setTimeout(() => setFocused(false), 150)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && hasQuery) doSearch(q);
              }}
              placeholder="搜索架构、协议或见解…"
              autoFocus
              className="flex-1 bg-transparent px-4 py-3 font-mono text-body-sm text-on-surface placeholder:text-outline focus:outline-none"
            />
            {isFetching && (
              <span className="flex items-center pr-4 text-on-surface-variant">
                <Loader2 size={16} className="animate-spin" />
              </span>
            )}
          </div>

          {/* 搜索历史 + 热门建议面板 */}
          {showPanel && (history.length > 0 || suggestionList.length > 0) && (
            <div className="absolute left-0 right-0 top-full z-30 mt-1 border border-outline-variant bg-surface-container-lowest shadow-lg">
              {/* 搜索历史 */}
              {history.length > 0 && (
                <div className="p-4 border-b border-outline-variant">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest flex items-center gap-1">
                      <Clock size={12} /> 搜索历史
                    </span>
                    <button
                      onMouseDown={(e) => {
                        e.preventDefault();
                        clearSearchHistory();
                        setHistory([]);
                      }}
                      className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest hover:text-error transition-colors"
                    >
                      清除
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {history.map((h) => (
                      <button
                        key={h}
                        onMouseDown={(e) => {
                          e.preventDefault();
                          doSearch(h);
                        }}
                        className="font-mono text-label-mono px-3 py-1 border border-outline-variant text-on-surface-variant hover:text-primary hover:border-primary transition-colors"
                      >
                        {h}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {/* 热门搜索建议 */}
              {suggestionList.length > 0 && (
                <div className="p-4">
                  <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest flex items-center gap-1 mb-2">
                    <Flame size={12} /> 热门文章
                  </span>
                  <ul>
                    {suggestionList.map((s, i) => (
                      <li key={s.slug}>
                        <button
                          onMouseDown={(e) => {
                            e.preventDefault();
                            doSearch(s.title);
                          }}
                          className="w-full text-left py-1.5 flex items-center gap-3 hover:bg-surface-container-low transition-colors px-2 -mx-2"
                        >
                          <span className="font-mono text-label-mono text-tertiary-fixed w-6 tabular-nums">
                            {String(i + 1).padStart(2, '0')}
                          </span>
                          <span className="flex-1 min-w-0 text-on-surface truncate">
                            {s.title}
                          </span>
                          {s.views > 0 && (
                            <span className="font-mono text-label-mono text-primary tabular-nums shrink-0">
                              ×{s.views}
                            </span>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 频道过滤 */}
        {hasQuery && channels.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            <button
              onClick={() => setChannel('')}
              className={cn(
                'font-mono text-label-mono uppercase tracking-widest px-3 py-1 border transition-colors',
                channel === ''
                  ? 'border-primary text-primary bg-primary/10'
                  : 'border-outline-variant text-on-surface-variant hover:text-primary',
              )}
            >
              全部
            </button>
            {channels.map((c) => (
              <button
                key={c.slug}
                onClick={() => setChannel(c.slug)}
                className={cn(
                  'font-mono text-label-mono uppercase tracking-widest px-3 py-1 border transition-colors',
                  channel === c.slug
                    ? 'border-primary text-primary bg-primary/10'
                    : 'border-outline-variant text-on-surface-variant hover:text-primary',
                )}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}

        {/* 结果区 */}
        <div className="mt-8">
          {!hasQuery ? (
            <p className="font-mono text-label-mono text-on-surface-variant mt-12 text-center uppercase tracking-widest">
              输入关键词，即时搜索全站文章
            </p>
          ) : isLoading ? (
            <p className="font-mono text-label-mono text-on-surface-variant mt-12 text-center uppercase tracking-widest">
              搜索中…
            </p>
          ) : hits.length === 0 ? (
            <p className="font-mono text-label-mono text-on-surface-variant mt-12 text-center uppercase tracking-widest">
              未找到「{q}」相关文章
            </p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
                  {total} RESULTS
                  {data?.processingTimeMs !== undefined && ` · ${data.processingTimeMs}MS`}
                </span>
              </div>
              <ul className="divide-y divide-outline-variant border-t border-outline-variant">
                {hits.map((h) => (
                  <li key={h.id}>
                    <Link
                      href={`/posts/${h.slug}`}
                      className="block py-6 hover:bg-surface-container-lowest transition-colors -mx-4 px-4"
                    >
                      <div className="flex items-center gap-3 mb-2">
                        {h.channelName && (
                          <span className="font-mono text-label-mono text-tertiary-fixed border border-tertiary-fixed/40 px-2 py-0.5 uppercase">
                            #{h.channelName}
                          </span>
                        )}
                        <span className="font-mono text-label-mono text-on-surface-variant uppercase">
                          {tsToDate(h.publishedAt)}
                          {h.readingTime ? ` · ${h.readingTime}MIN` : ''}
                        </span>
                      </div>
                      <h3
                        className="font-headline text-headline-sm text-primary mb-1 leading-snug"
                        dangerouslySetInnerHTML={{ __html: h._formatted.title }}
                      />
                      {h._formatted.excerpt && (
                        <p
                          className="font-sans text-body-sm text-on-surface-variant line-clamp-2"
                          dangerouslySetInnerHTML={{ __html: h._formatted.excerpt }}
                        />
                      )}
                      {h._formatted.content && (
                        <p
                          className="font-mono text-label-mono text-on-surface-variant mt-2 line-clamp-2"
                          dangerouslySetInnerHTML={{ __html: h._formatted.content }}
                        />
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
