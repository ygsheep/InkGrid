import Navbar from '@/components/layout/Navbar';

/**
 * Chat route group — full-height flex shell with navbar, no footer.
 * Lets the AI dialogue page own the entire viewport below the top bar.
 */
export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <main className="flex-1 pt-16 flex flex-col min-h-0">{children}</main>
    </div>
  );
}
