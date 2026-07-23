import type { MDXComponents } from 'mdx/types';
import { MDXRemote } from 'next-mdx-remote/rsc';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeSlug from 'rehype-slug';
import rehypeAutolinkHeadings from 'rehype-autolink-headings';
import rehypeHighlight from 'rehype-highlight';
// 代码高亮 + 数学公式样式（在 server component 中 import 即可全局生效）
import 'highlight.js/styles/atom-one-dark.css';
import 'katex/dist/katex.min.css';

/**
 * 博客文章 Markdown 渲染（Server Component）。
 *
 * 按 plan/前端模块设计文档.md 的渲染链：
 *   Markdown 源码 → remark/rehype 插件链 → HTML
 *
 * 插件：
 *   - remark-gfm        表格 / 任务列表 / 删除线
 *   - remark-math       数学公式语法解析
 *   - rehype-katex      KaTeX 渲染
 *   - rehype-slug       标题生成 id（支撑 TOC 锚点）
 *   - rehype-autolink-headings  标题自动加锚链接
 *   - rehype-highlight  代码块语法高亮（highlight.js）
 *
 * Mermaid / Shiki 后续 P1 接入。
 */
// 注：rehype-* 依赖 vfile@5，而 @mdx-js/mdx 内嵌 vfile@6，类型签名不兼容；
// 运行时 unified 鸭子类型兼容，故此处用 any 规避类型冲突。
const remarkPlugins: any[] = [remarkGfm, remarkMath];
const rehypePlugins: any[] = [
  rehypeSlug,
  [
    rehypeAutolinkHeadings,
    {
      behavior: 'append',
      properties: {
        className: ['anchor-link'],
        ariaHidden: 'true',
        tabIndex: -1,
      },
    },
  ],
  rehypeKatex,
  rehypeHighlight,
];

const components: MDXComponents = {
  // 在这里可以注入自定义组件，比如 <Callout>、<ObsidianCallout> 等
};

interface MarkdownContentProps {
  source: string;
}

export default function MarkdownContent({ source }: MarkdownContentProps) {
  return (
    <MDXRemote
      source={source}
      components={components}
      options={{
        mdxOptions: {
          remarkPlugins,
          rehypePlugins,
          format: 'md',
        },
      }}
    />
  );
}
