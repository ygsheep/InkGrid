'use client';

import { AntdRegistry } from '@ant-design/nextjs-registry';
import { ConfigProvider, App as AntdApp } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { darkTheme } from '@/lib/theme';

/**
 * 客户端 Providers：AntD Registry + ConfigProvider + App + React Query。
 * 必须放在 'use client' 边界内——darkTheme.algorithm 是函数，
 * 若在 Server Component 里直接用 ConfigProvider，theme 对象跨 RSC 网络边界时
 * 会在 stringify 阶段失败（Next 14 报 "at stringify (<anonymous>)" 500）。
 */
export default function Providers({ children }: { children: React.ReactNode }) {
  // QueryClient 在组件内创建，保证每个用户会话独立实例（SSR 安全）
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  );

  return (
    <AntdRegistry>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider theme={darkTheme}>
          <AntdApp>{children}</AntdApp>
        </ConfigProvider>
      </QueryClientProvider>
    </AntdRegistry>
  );
}
