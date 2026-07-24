'use client';

import { useState } from 'react';
import { Check, Copy, RotateCcw, ThumbsDown, ThumbsUp } from 'lucide-react';

/**
 * 消息操作栏：复制 / 重试 / 点赞 / 点踩。
 *
 * 仅前端 UI 状态，点赞点踩不持久化到后端（刷新后重置）。
 * 复制用 navigator.clipboard.writeText，兼容性：HTTPS 或 localhost。
 *
 * Props：
 * - content：要复制的文本内容
 * - onRetry：重试回调（仅 assistant 消息有，user 消息不传）
 * - feedback：外部受控的反馈状态（'up' | 'down' | null），可选
 * - onFeedback：反馈回调，可选（不传则纯内部状态）
 * - compact：紧凑模式（用户消息底部只有复制按钮）
 */
interface MessageActionsProps {
  content: string;
  onRetry?: () => void;
  compact?: boolean;
}

export function MessageActions({ content, onRetry, compact }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard API 在非 HTTPS / 非 localhost 下可能不可用，静默失败
    }
  };

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedback((prev) => (prev === type ? null : type));
  };

  return (
    <div className="flex items-center gap-1 mt-2 -mb-1">
      {/* 复制 */}
      <button
        type="button"
        onClick={handleCopy}
        className="p-1.5 text-tertiary-fixed hover:text-on-surface hover:bg-surface-container-low transition-colors"
        title="复制"
        aria-label="复制"
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>

      {/* 重试（仅 assistant） */}
      {!compact && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="p-1.5 text-tertiary-fixed hover:text-on-surface hover:bg-surface-container-low transition-colors"
          title="重试"
          aria-label="重试"
        >
          <RotateCcw size={14} />
        </button>
      )}

      {/* 点赞 / 点踩（仅 assistant） */}
      {!compact && (
        <>
          <button
            type="button"
            onClick={() => handleFeedback('up')}
            className={`p-1.5 transition-colors ${
              feedback === 'up'
                ? 'text-primary bg-surface-container-low'
                : 'text-tertiary-fixed hover:text-on-surface hover:bg-surface-container-low'
            }`}
            title="有用"
            aria-label="有用"
          >
            <ThumbsUp size={14} />
          </button>
          <button
            type="button"
            onClick={() => handleFeedback('down')}
            className={`p-1.5 transition-colors ${
              feedback === 'down'
                ? 'text-error bg-surface-container-low'
                : 'text-tertiary-fixed hover:text-on-surface hover:bg-surface-container-low'
            }`}
            title="无用"
            aria-label="无用"
          >
            <ThumbsDown size={14} />
          </button>
        </>
      )}
    </div>
  );
}
