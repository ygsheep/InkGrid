/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
    ],
  },
  // Bytemd 及其插件是 ESM，需 transpile 才能在 Next 14 中正常打包
  transpilePackages: [
    'bytemd',
    '@bytemd/react',
    '@bytemd/plugin-gfm',
    '@bytemd/plugin-highlight',
    '@bytemd/plugin-math',
    '@bytemd/plugin-mermaid',
    'remark-gfm',
    'remark-math',
    'rehype-highlight',
    'rehype-katex',
    'rehype-mermaid',
    'katex',
  ],
  // 注：Next 14.2 已默认对 antd 做模块优化，
  // 不再手动加 optimizePackageImports（会触发 RSC manifest 找不到 antd 客户端入口的运行时错误）。
};

module.exports = nextConfig;
