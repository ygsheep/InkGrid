'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Editor } from '@bytemd/react';
import type { BytemdPlugin } from 'bytemd';
import gfm from '@bytemd/plugin-gfm';
import highlight from '@bytemd/plugin-highlight';
import math from '@bytemd/plugin-math';
import mermaid from '@bytemd/plugin-mermaid';
import 'bytemd/dist/index.min.css';
import { uploadsApi } from '@/lib/api/admin';
import WikilinkSuggest, { type WikilinkItem } from './WikilinkSuggest';

/**
 * 后台 Markdown 编辑器:源码 + 预览分屏。
 *
 * Bytemd 插件链与博客展示端保持一致,保证所见即所得。
 * 值由父组件受控,onChange 回吐 Markdown 源码。
 *
 * 图片上传:
 * - 粘贴图片(Ctrl+V)→ 自动上传 → 插入 Markdown 图片链接
 * - 拖拽图片到编辑器 → 自动上传 → 插入
 * - 工具栏图片按钮 → 选择文件 → 上传 → 插入
 *
 * 双链补全（enableWikilink=true）:
 * - 输入 [[ 时弹出笔记搜索浮层
 * - ↑↓ 选择 · Enter 确认 · Esc 关闭
 * - 选中后插入 [[标题]]
 */
const basePlugins = [gfm(), highlight(), math(), mermaid()];

/** 上传图片到后端,返回 Markdown 图片语法字符串 */
async function uploadImage(file: File): Promise<string> {
  const result = await uploadsApi.uploadImage(file);
  const alt = file.name.replace(/\.[^.]+$/, ''); // 去扩展名作为 alt
  return `![${alt}](${result.url})`;
}

/** 判断是否为图片文件 */
function isImageFile(file: File): boolean {
  return file.type.startsWith('image/');
}

interface MarkdownEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  /** 启用双链 [[ 补全 */
  enableWikilink?: boolean;
  /** 笔记搜索函数（enableWikilink=true 时必传） */
  searchNotes?: (q: string) => Promise<WikilinkItem[]>;
  /** 排除的笔记 id（避免自引用） */
  excludeNoteId?: string;
}

/** 双链补全上下文 */
interface SuggestState {
  query: string;
  from: { line: number; ch: number };
  to: { line: number; ch: number };
  left: number;
  top: number;
}

export default function MarkdownEditor({
  value = '',
  onChange,
  placeholder,
  enableWikilink = false,
  searchNotes,
  excludeNoteId,
}: MarkdownEditorProps) {
  // CodeMirror 实例（CM5）。用 any 规避 @types/codemirror 版本差异。
  const cmRef = useRef<any>(null);
  // 搜索函数用 ref 保持稳定，避免 plugin 重建
  const searchNotesRef = useRef(searchNotes);
  searchNotesRef.current = searchNotes;
  const excludeRef = useRef(excludeNoteId);
  excludeRef.current = excludeNoteId;

  const [suggest, setSuggest] = useState<SuggestState | null>(null);
  const [results, setResults] = useState<WikilinkItem[]>([]);
  const [loading, setLoading] = useState(false);

  /** 检测光标前是否为 [[xxx 上下文 */
  const detectWikilink = useCallback((cm: any) => {
    const cursor = cm.getCursor();
    const line = cm.getLine(cursor.line);
    const before = line.slice(0, cursor.ch);
    // 匹配未闭合的 [[，排除 ![[ 嵌入语法
    const m = before.match(/(?<!!)\[\[([^\]\n|]*)$/);
    if (m) {
      const query = m[1];
      const from = {
        line: cursor.line,
        ch: cursor.ch - query.length - 2, // [[ 之后
      };
      const to = { line: cursor.line, ch: cursor.ch };
      const coords = cm.cursorCoords(true, 'window');
      setSuggest({ query, from, to, left: coords.left, top: coords.bottom });
    } else {
      setSuggest(null);
    }
  }, []);

  /** 插入选中的双链 */
  const insertLink = useCallback(
    (item: WikilinkItem) => {
      const cm = cmRef.current;
      if (!cm || !suggest) return;
      const text = `[[${item.title}]]`;
      cm.replaceRange(text, suggest.from, suggest.to);
      setSuggest(null);
      cm.focus();
    },
    [suggest],
  );

  /** wikilink 插件：通过 editorEffect 拿 CM 实例并监听 change */
  const wikilinkPlugin = useMemo<BytemdPlugin>(() => {
    return {
      editorEffect(ctx: any) {
        const cm = ctx.editor;
        cmRef.current = cm;
        const handler = () => detectWikilink(cm);
        cm.on('change', handler);
        return () => {
          cm.off('change', handler);
        };
      },
    };
  }, [detectWikilink]);

  const plugins = useMemo(
    () => (enableWikilink ? [...basePlugins, wikilinkPlugin] : basePlugins),
    [enableWikilink, wikilinkPlugin],
  );

  // 搜索（防抖 200ms）
  useEffect(() => {
    if (!suggest || !searchNotesRef.current) {
      setResults([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const items = await searchNotesRef.current!(suggest.query);
        if (!cancelled) {
          setResults(items.filter((i) => i.id !== excludeRef.current));
        }
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [suggest]);

  /** 处理粘贴事件:检测图片文件并上传 */
  const handlePaste = useCallback(
    async (e: React.ClipboardEvent<HTMLDivElement>) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.kind === 'file') {
          const file = item.getAsFile();
          if (file && isImageFile(file)) {
            e.preventDefault();
            try {
              const md = await uploadImage(file);
              onChange?.(value + (value.endsWith('\n') || value === '' ? '' : '\n') + md + '\n');
            } catch (err) {
              console.error('图片上传失败:', err);
            }
            break;
          }
        }
      }
    },
    [value, onChange],
  );

  /** 处理拖拽事件:检测图片文件并上传 */
  const handleDrop = useCallback(
    async (e: React.DragEvent<HTMLDivElement>) => {
      const files = e.dataTransfer?.files;
      if (!files || files.length === 0) return;
      const imageFiles = Array.from(files).filter(isImageFile);
      if (imageFiles.length === 0) return;
      e.preventDefault();
      const mds: string[] = [];
      for (const file of imageFiles) {
        try {
          mds.push(await uploadImage(file));
        } catch (err) {
          console.error('图片上传失败:', err);
        }
      }
      if (mds.length > 0) {
        const insertion = mds.join('\n') + '\n';
        onChange?.(value + (value.endsWith('\n') || value === '' ? '' : '\n') + insertion);
      }
    },
    [value, onChange],
  );

  return (
    <div className="bytemd-wrapper" onPaste={handlePaste} onDrop={handleDrop}>
      <Editor
        value={value}
        plugins={plugins}
        placeholder={placeholder}
        onChange={onChange}
      />
      {enableWikilink && (
        <WikilinkSuggest
          visible={!!suggest}
          items={results}
          loading={loading}
          position={suggest ? { left: suggest.left, top: suggest.top } : null}
          onSelect={insertLink}
          onClose={() => setSuggest(null)}
        />
      )}
    </div>
  );
}
