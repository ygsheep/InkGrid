/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
    ],
  },
  // 注：Next 14.2 已默认对 antd 做模块优化，
  // 不再手动加 optimizePackageImports（会触发 RSC manifest 找不到 antd 客户端入口的运行时错误）。
};

module.exports = nextConfig;
