import Navbar from '@/components/layout/Navbar';
import Footer from '@/components/layout/Footer';

/**
 * Public site layout: fixed TopNavBar + edge-to-edge content + Footer.
 * Spatial grid is applied per-page (home/list/channel) — the article detail
 * page and admin use a flat surface to favour long-form reading.
 *
 * 频道列表由 Navbar 内部 useChannels 拉取并缓存,(public) 与 (chat) 共享,
 * 保证导航在任何路由下一致。
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
