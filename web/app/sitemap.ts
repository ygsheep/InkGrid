import type { MetadataRoute } from 'next';
import { fetchPosts, fetchChannels } from '@/lib/api';

const BASE = 'https://inkgrid.dev';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, lastModified: now, changeFrequency: 'daily', priority: 1 },
    { url: `${BASE}/about`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
  ];

  const postRoutes: MetadataRoute.Sitemap = [];
  try {
    const { items } = await fetchPosts({ size: 1000 });
    for (const p of items) {
      postRoutes.push({
        url: `${BASE}/posts/${p.slug}`,
        lastModified: p.publishedAt ? new Date(p.publishedAt) : now,
        changeFrequency: 'weekly',
        priority: 0.8,
      });
    }
  } catch {
    // 后端不可用时降级为空
  }

  const channelRoutes: MetadataRoute.Sitemap = [];
  try {
    const channels = await fetchChannels();
    for (const c of channels) {
      channelRoutes.push({
        url: `${BASE}/channel?channel=${c.slug}`,
        lastModified: now,
        changeFrequency: 'weekly',
        priority: 0.7,
      });
    }
  } catch {
    // 后端不可用时降级为空
  }

  return [...staticRoutes, ...postRoutes, ...channelRoutes];
}
