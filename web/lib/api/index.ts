/**
 * 公开 API 接口封装。
 * Server Component 用 serverFetch（带 Next 缓存），Client Component 用 request。
 *
 * 路径约定：path 不带 /api 前缀，由 NEXT_PUBLIC_API_BASE 统一拼接：
 *  - dev:  NEXT_PUBLIC_API_BASE=http://localhost:8000/api
 *  - prod: NEXT_PUBLIC_API_BASE=/api
 */
import type { Article, ArticleSummary, Channel, Citation, Persona } from '@/types';
import { request, serverFetch } from './request';

// ===== 类型 =====

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface AboutInfo {
  siteName: string;
  author: string;
  version: string;
  extra?: Record<string, unknown>;
}

// ===== Server-side（RSC 用）=====

export async function fetchPosts(opts?: {
  page?: number;
  size?: number;
  channel?: string;
  tag?: string;
  q?: string;
  revalidate?: number;
}): Promise<Paginated<ArticleSummary>> {
  const params = new URLSearchParams();
  if (opts?.page) params.set('page', String(opts.page));
  if (opts?.size) params.set('size', String(opts.size));
  if (opts?.channel) params.set('channel', opts.channel);
  if (opts?.tag) params.set('tag', opts.tag);
  if (opts?.q) params.set('q', opts.q);
  const qs = params.toString();
  return serverFetch<Paginated<ArticleSummary>>(`/posts${qs ? `?${qs}` : ''}`, {
    tags: ['posts'],
  });
}

export async function fetchPost(slug: string): Promise<Article> {
  return serverFetch<Article>(`/posts/${slug}`, { tags: ['posts', `post:${slug}`] });
}

export interface AdjacentPost {
  slug: string;
  title: string;
  channel: string;
  channelName: string;
  publishedAt: string;
}

export interface AdjacentPosts {
  prev: AdjacentPost | null;
  next: AdjacentPost | null;
}

export async function fetchAdjacentPosts(slug: string): Promise<AdjacentPosts> {
  return serverFetch<AdjacentPosts>(`/posts/${slug}/adjacent`, {
    tags: ['posts', `post:${slug}`],
  });
}

export interface TagWithCount {
  tag: string;
  count: number;
}

export async function fetchChannelTags(
  slug: string,
  revalidate = 300,
): Promise<{ items: TagWithCount[]; total: number }> {
  return serverFetch(`/channels/${slug}/tags`, { tags: ['posts'], revalidate });
}

export async function fetchChannels(revalidate = 300): Promise<Channel[]> {
  const res = await serverFetch<Paginated<Channel>>('/channels', { revalidate });
  return res.items;
}

export async function fetchChannel(slug: string, revalidate = 300): Promise<Channel> {
  return serverFetch<Channel>(`/channels/${slug}`, { revalidate });
}

export async function fetchChannelPosts(
  slug: string,
  opts?: { tag?: string; page?: number; size?: number },
): Promise<{ items: ArticleSummary[]; total: number }> {
  const params = new URLSearchParams();
  if (opts?.tag) params.set('tag', opts.tag);
  if (opts?.page) params.set('page', String(opts.page));
  if (opts?.size) params.set('size', String(opts.size));
  const qs = params.toString();
  const res = await serverFetch<Paginated<ArticleSummary>>(
    `/channels/${slug}/posts${qs ? `?${qs}` : ''}`,
    { tags: ['posts'] },
  );
  return { items: res.items, total: res.total };
}

export async function fetchPersonas(revalidate = 300): Promise<Persona[]> {
  const res = await serverFetch<Paginated<Persona>>('/personas', { revalidate });
  return res.items;
}

export async function fetchAbout(revalidate = 3600): Promise<AboutInfo> {
  return serverFetch<AboutInfo>('/about', { revalidate });
}

// ===== 搜索（Meilisearch）=====

/** 搜索命中字段含 <mark> 高亮标签 */
export interface SearchHit {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  channelSlug: string;
  channelName: string;
  tags: string[];
  publishedAt: number; // unix timestamp
  readingTime: number;
  _formatted: {
    title: string;
    excerpt: string;
    content: string;
  };
}

export interface SearchResponse {
  hits: SearchHit[];
  estimatedTotalHits: number;
  processingTimeMs: number;
  query: string;
}

export interface SearchSuggestion {
  slug: string;
  title: string;
  views: number;
}

// ===== Chat Session（公开问答会话）=====

export interface ChatSessionCreatePayload {
  persona_id?: string | null;
  scope_type?: 'global' | 'channel' | 'article';
  scope_ref?: string | null;
  title?: string | null;
}

export interface ChatSessionOut {
  id: string;
  anon_id: string | null;
  persona_id: string | null;
  scope_type: string;
  scope_ref: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageOut {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[] | null;
  follow_ups?: string[] | null;
  created_at: string;
}

// ===== Client-side（'use client' 组件用）=====
// 注意：response interceptor 已 unwrap envelope，request.get 返回的是 data 本身。
// 这里用 as 断言修正类型。
function unwrap<T>(p: Promise<unknown>): Promise<T> {
  return p as Promise<T>;
}

export const api = {
  async getPosts(params?: { page?: number; size?: number; channel?: string }) {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.size) qs.set('size', String(params.size));
    if (params?.channel) qs.set('channel', params.channel);
    return unwrap<Paginated<ArticleSummary>>(
      request.get(`/posts${qs.toString() ? `?${qs}` : ''}`),
    );
  },
  async getPost(slug: string) {
    return unwrap<Article>(request.get(`/posts/${slug}`));
  },
  async getChannels() {
    return unwrap<Paginated<Channel>>(request.get('/channels'));
  },
  async getChannel(slug: string) {
    return unwrap<Channel>(request.get(`/channels/${slug}`));
  },
  async getChannelPosts(slug: string) {
    return unwrap<Paginated<ArticleSummary>>(request.get(`/channels/${slug}/posts`));
  },
  async getPersonas() {
    return unwrap<Paginated<Persona>>(request.get('/personas'));
  },
  async getAbout() {
    return unwrap<AboutInfo>(request.get('/about'));
  },
  async search(params: { q: string; limit?: number; channel?: string }) {
    const qs = new URLSearchParams({ q: params.q });
    if (params.limit) qs.set('limit', String(params.limit));
    if (params.channel) qs.set('channel', params.channel);
    return unwrap<SearchResponse>(request.get(`/search?${qs}`));
  },
  async searchSuggestions(limit = 5) {
    return unwrap<{ suggestions: SearchSuggestion[] }>(
      request.get(`/search/suggestions?limit=${limit}`),
    );
  },
  // ===== Chat Session =====
  async createChatSession(payload: ChatSessionCreatePayload = {}) {
    return unwrap<ChatSessionOut>(request.post('/chat/sessions', payload));
  },
  async listChatSessions(page = 1, size = 20) {
    return unwrap<Paginated<ChatSessionOut>>(
      request.get(`/chat/sessions?page=${page}&size=${size}`),
    );
  },
  async listChatMessages(sessionId: string, limit = 100) {
    return unwrap<Paginated<ChatMessageOut>>(
      request.get(`/chat/sessions/${sessionId}/messages?limit=${limit}`),
    );
  },
};
