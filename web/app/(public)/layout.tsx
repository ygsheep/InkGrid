import Navbar from '@/components/layout/Navbar';
import Footer from '@/components/layout/Footer';

/**
 * Public site layout: fixed TopNavBar + edge-to-edge content + Footer.
 * Spatial grid is applied per-page (home/list/channel) — the article detail
 * page and admin use a flat surface to favour long-form reading.
 *
 * 频道入口为单个 /channel 路由,频道切换在频道页内通过横向 chips 完成。
 * useChannels 由搜索页等客户端组件按需使用并共享 React Query 缓存。
 */
export default async function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <main className="flex-1 pt-16">{children}</main>
      <Footer />
    </div>
  );
}
