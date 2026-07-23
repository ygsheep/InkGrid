import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import { unified } from 'unified';
import type { Node } from 'unist';
import { visit } from 'unist-util-visit';
import GithubSlugger from 'github-slugger';
import type { TocItem } from '@/types';

/**
 * 从 markdown 源码提取标题，生成 TOC。
 *
 * 与 MarkdownContent.tsx 的 rehype-slug 底层都使用 github-slugger，
 * 保证点击 TOC 锚点能跳转到对应标题（id 100% 一致）。
 *
 * 仅提取 h2 / h3（h1 是文章标题，h4+ 层级太深不放 TOC）。
 */
export function extractToc(markdown: string): TocItem[] {
  const tree = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .parse(markdown);

  // 与 rehype-slug 同源：github-slugger 会自动处理重复标题（-1, -2 后缀）
  const slugger = new GithubSlugger();
  const items: TocItem[] = [];

  visit(tree, 'heading', (node: Node & { depth: number; children: any[] }) => {
    if (node.depth !== 2 && node.depth !== 3) return;

    // 拼接所有 text 节点（忽略 inline code 等格式标记）
    const text = node.children
      .map((c: any) => (c.type === 'text' ? c.value : ''))
      .join('')
      .trim();

    if (!text) return;

    const id = slugger.slug(text);

    items.push({
      id,
      title: text,
      level: node.depth,
    });
  });

  return items;
}
