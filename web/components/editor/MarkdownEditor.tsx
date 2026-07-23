'use client';

import { useCallback } from 'react';
import { Editor } from '@bytemd/react';
import gfm from '@bytemd/plugin-gfm';
import highlight from '@bytemd/plugin-highlight';
import math from '@bytemd/plugin-math';
import mermaid from '@bytemd/plugin-mermaid';
import 'bytemd/dist/index.min.css';
import { uploadsApi } from '@/lib/api/admin';

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
 */
const plugins = [
  gfm(),
  highlight(),
  math(),
  mermaid(),
];

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
}

export default function MarkdownEditor({
  value = '',
  onChange,
  placeholder,
}: MarkdownEditorProps) {
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
              // 在当前光标位置插入图片 Markdown
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
    <div
      className="bytemd-wrapper"
      onPaste={handlePaste}
      onDrop={handleDrop}
    >
      <Editor
        value={value}
        plugins={plugins}
        placeholder={placeholder}
        onChange={onChange}
      />
    </div>
  );
}
