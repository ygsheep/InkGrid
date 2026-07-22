/**
 * 公开 API 接口封装。
 * Server Component 用 serverFetch（带 Next 缓存），Client Component 用 request。
 *
 * 路径约定：path 不带 /api 前缀，由 NEXT_PUBLIC_API_BASE 统一拼接：
 *  - dev:  NEXT_PUBLIC_API_BASE=http://localhost:8000/api
 *  - prod: NEXT_PUBLIC_API_BASE=/api
 */
import type { Article, ArticleSummary, Channel, Persona } from '@/types';
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
  revalidate?: number;
}): Promise<Paginated<ArticleSummary>> {
  const params = new URLSearchParams();
  if (opts?.page) params.set('page', String(opts.page));
  if (opts?.size) params.set('size', String(opts.size));
  if (opts?.channel) params.set('channel', opts.channel);
  const qs = params.toString();
  return serverFetch<Paginated<ArticleSummary>>(`/posts${qs ? `?${qs}` : ''}`, {
    revalidate: opts?.revalidate ?? 60,
  });
}

export async function fetchPost(slug: string, revalidate = 60): Promise<Article> {
  return serverFetch<Article>(`/posts/${slug}`, { revalidate });
}

export async function fetchChannels(revalidate = 300): Promise<Channel[]> {
  const res = await serverFetch<Paginated<Channel>>('/channels', { revalidate });
  return res.items;
}

export async function fetchChannel(slug: string, revalidate = 300): Promise<Channel> {
  return serverFetch<Channel>(`/channels/${slug}`, { revalidate });
}

export async function fetchChannelPosts(slug: string, revalidate = 60): Promise<ArticleSummary[]> {
  const res = await serverFetch<Paginated<ArticleSummary>>(`/channels/${slug}/posts`, {
    revalidate,
  });
  return res.items;
}

export async function fetchPersonas(revalidate = 300): Promise<Persona[]> {
  const res = await serverFetch<Paginated<Persona>>('/personas', { revalidate });
  return res.items;
}

export async function fetchAbout(revalidate = 3600): Promise<AboutInfo> {
  return serverFetch<AboutInfo>('/about', { revalidate });
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
};
