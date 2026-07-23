'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

/**
 * useSearch — Meilisearch 即时搜索，带 300ms debounce。
 *
 * q 为空时不发请求；q 变化后 debounce 300ms 才真正查询，避免每个按键打后端。
 * staleTime 60s：短时间内重复搜同一关键词走缓存。
 */
export function useSearch(q: string, opts?: { limit?: number; channel?: string }) {
  const [debounced, setDebounced] = useState(q);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  return useQuery({
    queryKey: ['search', debounced, opts?.limit ?? 10, opts?.channel ?? ''],
    queryFn: () => api.search({ q: debounced, limit: opts?.limit, channel: opts?.channel }),
    enabled: debounced.trim().length > 0,
    staleTime: 60_000,
  });
}

/** 热门搜索建议（按文章访问量排序） */
export function useSearchSuggestions(limit = 5) {
  return useQuery({
    queryKey: ['search', 'suggestions', limit],
    queryFn: () => api.searchSuggestions(limit),
    staleTime: 5 * 60_000,
  });
}

const HISTORY_KEY = 'inkgrid:search-history';
const HISTORY_MAX = 8;

/** 搜索历史（localStorage，最近 8 条，去重） */
export function getSearchHistory(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addSearchHistory(q: string) {
  if (typeof window === 'undefined' || !q.trim()) return;
  const trimmed = q.trim();
  const history = getSearchHistory().filter((h) => h !== trimmed);
  history.unshift(trimmed);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, HISTORY_MAX)));
}

export function clearSearchHistory() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(HISTORY_KEY);
}
