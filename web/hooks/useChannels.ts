'use client';

import { useQuery } from '@tanstack/react-query';
import { request } from '@/lib/api/request';
import type { Channel } from '@/types';

interface Paginated<T> {
  items: T[];
  total: number;
}

/**
 * useChannels — 公开频道列表(导航栏用)。
 *
 * 客户端 React Query 缓存,staleTime 5 分钟,路由切换不重复请求。
 * Navbar 在 (public) 和 (chat) 两个路由组共享同一缓存,保证导航一致。
 */
export function useChannels() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: () => request.get<unknown, Paginated<Channel>>('/channels'),
    staleTime: 5 * 60 * 1000,
    select: (data) => data.items.map((c) => ({ slug: c.slug, name: c.name })),
  });
}
