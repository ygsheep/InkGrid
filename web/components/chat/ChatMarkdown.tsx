'use client';

import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeHighlight from 'rehype-highlight';
// 代码高亮 + 数学公式样式（与文章详情页 MarkdownContent 保持一致）
import 'highlight.js/styles/atom-one-dark.css';
import 'katex/dist/katex.min.css';

/**
 * 聊天消息 Markdown 渲染（Client Component）。
 *
 * 与文章详情页的 MarkdownContent（next-mdx-remote/rsc）保持插件链一致：
 *   - remark-gfm      表格 / 任务列表 / 删除线
 *   - remark-math     数学公式语法解析
 *   - rehype-katex    KaTeX 渲染
 *   - rehype-highlight 代码块语法高亮（highlight.js）
 *
 * 区别于文章页：
 *   - 不用 rehype-slug / rehype-autolink-headings（聊天消息无需 TOC 锚点）
 *   - 用 react-markdown 支持流式增量渲染（content 边接收边渲染）
 *   - 自定义 components 适配深色气泡背景与紧凑布局
 *
 * 注：rehype-* 依赖 vfile@5，与 react-markdown 内置类型签名不完全一致，
 * 运行时 unified 鸭子类型兼容，这里用 any 规避类型冲突（与 MarkdownContent 同样处理）。
 */
const remarkPlugins: any[] = [remarkGfm, remarkMath];
const rehypePlugins: any[] = [rehypeKatex, rehypeHighlight];

/**
 * 自定义组件映射：让 md 元素适配聊天气泡的深色背景与紧凑布局。
 *
 * 文章页用 prose 类统一样式，聊天页这里用 components 逐元素控制，
 * 避免引入 @tailwindcss/typography 的 prose 主题覆盖。
 */
const components: Components = {
  // 段落：紧凑间距，避免大段空白
  p: ({ children }) => <p className="my-2 leading-relaxed">{children}</p>,
  // 标题：缩小字号，避免聊天里标题过大
  h1: ({ children }) => <h1 className="text-lg font-bold mt-4 mb-2">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-bold mt-3 mb-2">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-bold mt-3 mb-1">{children}</h3>,
  h4: ({ children }) => <h4 className="text-sm font-semibold mt-2 mb-1">{children}</h4>,
  h5: ({ children }) => <h5 className="text-xs font-semibold mt-2 mb-1">{children}</h5>,
  h6: ({ children }) => <h6 className="text-xs font-semibold mt-2 mb-1">{children}</h6>,
  // 列表：紧凑
  ul: ({ children }) => <ul className="my-2 ml-5 list-disc space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 ml-5 list-decimal space-y-1">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  // 代码块：深色背景 + 横向滚动（atom-one-dark 主题）
  pre: ({ children }) => (
    <pre className="my-3 p-3 bg-[#282c34] overflow-x-auto text-sm font-mono">
      {children}
    </pre>
  ),
  // 行内代码：浅灰背景 + 等宽
  code: ({ className, children, ...props }) => {
    // 含 language-xxx 类的是代码块（已被 pre 包裹），这里只处理行内
    const isBlock = /language-/.test(className || '');
    if (isBlock) {
      return <code className={className} {...props}>{children}</code>;
    }
    return (
      <code className="px-1 py-0.5 bg-surface-container-high text-on-surface rounded text-sm font-mono" {...props}>
        {children}
      </code>
    );
  },
  // 引用块：左侧竖线
  blockquote: ({ children }) => (
    <blockquote className="my-2 pl-3 border-l-2 border-tertiary-fixed text-on-surface-variant">
      {children}
    </blockquote>
  ),
  // 表格：横向滚动
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-surface-container-low">{children}</thead>,
  th: ({ children }) => (
    <th className="border border-outline-variant px-3 py-1.5 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border border-outline-variant px-3 py-1.5">{children}</td>
  ),
  // 链接：新标签页打开（避免离开对话页）
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary-fixed underline hover:text-primary"
    >
      {children}
    </a>
  ),
  // 分隔线
  hr: () => <hr className="my-4 border-outline-variant" />,
};

interface ChatMarkdownProps {
  /** Markdown 源文本（流式时会增量更新） */
  content: string;
}

/**
 * 聊天 Markdown 渲染器。
 *
 * 用 memo 包裹避免父组件流式 re-render 时不必要的重渲染
 * （content 不变时跳过，content 变化时才重新解析渲染）。
 */
function ChatMarkdownImpl({ content }: ChatMarkdownProps) {
  return (
    <div className="font-sans text-body-md text-on-surface chat-markdown">
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export const ChatMarkdown = memo(ChatMarkdownImpl);
