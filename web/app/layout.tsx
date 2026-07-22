import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { JetBrains_Mono } from 'next/font/google';
import Providers from './providers';
import './globals.css';

const siteName = process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev';
const author = process.env.NEXT_PUBLIC_SITE_AUTHOR || '博主';

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: siteName,
    template: `%s · ${siteName}`,
  },
  description: `${author} 的个人博客与 AI 知识库问答`,
  metadataBase: new URL('https://example.com'),
  openGraph: {
    title: siteName,
    description: `${author} 的个人博客与 AI 知识库问答`,
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="zh-CN"
      className={`${GeistSans.variable} ${jetbrains.variable}`}
      suppressHydrationWarning
    >
      <body className="font-sans bg-background text-on-surface antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
