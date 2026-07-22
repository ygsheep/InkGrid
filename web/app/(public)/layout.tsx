import Navbar from '@/components/layout/Navbar';
import Footer from '@/components/layout/Footer';
import { fetchChannels } from '@/lib/api';

/**
 * Public site layout: fixed TopNavBar + edge-to-edge content + Footer.
 * Spatial grid is applied per-page (home/list/channel) — the article detail
 * page and admin use a flat surface to favour long-form reading.
 *
 * 频道列表在 RSC 层拉取并传入 Navbar，避免 Client Component 内部 fetch
 * 导致的鉴权/缓存问题，同时让导航链接始终与后端数据一致。
 */
export default async function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let channels: { slug: string; name: string }[] = [];
  try {
    channels = (await fetchChannels()).map((c) => ({ slug: c.slug, name: c.name }));
  } catch {
    // 后端不可用时降级为空数组，Navbar 仅渲染固定链接
    channels = [];
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar channels={channels} />
      <main className="flex-1 pt-16">{children}</main>
      <Footer />
    </div>
  );
}
