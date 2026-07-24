'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Drawer } from 'antd';
import {
  ArrowLeft,
  Mic,
  Send,
  Plus,
  Phone,
  User,
  ChevronDown,
  Check,
  Square,
  AlertCircle,
  FileText,
  Brain,
} from 'lucide-react';
import { usePersona } from '@/lib/usePersona';
import { useChat, type ChatMsg } from '@/hooks/useChat';
import { cn } from '@/lib/utils';
import { ChatMarkdown } from '@/components/chat/ChatMarkdown';
import { MessageActions } from '@/components/chat/MessageActions';

const quickCommands = ['/状态报告', '/知识库概览', '/最新文章', '/清空会话'];

/**
 * AI 对话页 — 终端式沉浸聊天 UI。
 * 接入后端 /ws/chat 流式问答（useChat hook），支持：
 *  - token 流式渲染 + 光标
 *  - citation 引用溯源（可跳转文章详情）
 *  - followup 追问建议（可点击作为下一问）
 *  - clarify 澄清请求（带选项按钮）
 *  - error / rate / stop / 重连
 */
export default function AskPage() {
  // 初始欢迎语：timestamp 留空，hydration 后补设，避免 SSR 不一致
  const [initialMessages] = useState<ChatMsg[]>(() => [
    {
      kind: 'assistant',
      content:
        '上行链路已建立。我基于博主的文章知识库回答你的问题——每一次回答都会标注引用出处。请发送指令或提问。',
      streaming: false,
      timestamp: '',
    },
  ]);

  const { persona, personaId, personas, select, hydrated } = usePersona();
  const {
    messages: chatMessages,
    streaming,
    connected,
    connecting,
    remaining,
    send,
    stop,
    reset,
  } = useChat({
    personaId,
    scopeType: 'global',
    initialMessages,
  });

  const [input, setInput] = useState('');
  const [focused, setFocused] = useState(false);
  const [personaDrawerOpen, setPersonaDrawerOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 从首页/文章页带过来的初始问题
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    if (q) {
      setInput(q);
      setTimeout(() => send(q), 120);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chatMessages, streaming]);

  // textarea 自动伸缩
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  }, [input]);

  const onSubmit = (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || streaming || connecting) return;
    // 快捷命令：清空会话
    if (q === '/清空会话') {
      reset();
      setInput('');
      return;
    }
    send(q);
    setInput('');
  };

  // 点击追问 / clarify 选项 → 作为下一问
  const askAgain = (text: string) => {
    if (streaming || connecting) return;
    send(text);
  };

  // 重试：找到当前 assistant 消息的前一条 user 消息，重新发送
  const retryLast = (assistantIndex: number) => {
    if (streaming || connecting) return;
    // 向前找最近的 user 消息
    for (let j = assistantIndex - 1; j >= 0; j--) {
      if (chatMessages[j].kind === 'user') {
        send(chatMessages[j].content);
        return;
      }
    }
  };

  // 首个 reasoning/content 到达前显示"AI 正在思考"占位
  const lastMsg = chatMessages[chatMessages.length - 1];
  const waitingFirstToken =
    streaming && !(lastMsg?.kind === 'assistant' && !!lastMsg.streaming);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] min-h-0">
      {/* 实体头 — 角色切换 + 状态指示 + 语音通话（紧凑单行，突出内容区） */}
      <header className="border-b border-outline-variant bg-black/70 backdrop-blur-md z-40">
        <div className="mx-auto max-w-chat px-margin-mobile md:px-margin-desktop py-2 flex justify-between items-center gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              onClick={() => {
                if (window.history.length > 1) window.history.back();
                else window.location.href = '/';
              }}
              className="p-1 -ml-1 text-on-surface-variant hover:text-primary transition-colors shrink-0"
              aria-label="返回"
            >
              <ArrowLeft size={16} />
            </button>
            <div className="w-7 h-7 border border-outline bg-surface-container flex items-center justify-center shrink-0">
              <User size={14} className="text-primary" />
            </div>
            {/* 角色切换按钮 — 单行紧凑布局 */}
            <button
              onClick={() => setPersonaDrawerOpen(true)}
              className="flex items-center gap-1.5 min-w-0 text-left group"
              aria-label="切换角色"
            >
              <span className="font-headline text-headline-sm text-primary uppercase tracking-tighter leading-none truncate">
                {hydrated ? persona.name : 'AI 节点'}
              </span>
              <ChevronDown
                size={12}
                className="text-on-surface-variant group-hover:text-primary transition-colors shrink-0"
              />
              {/* 连接状态指示灯 + tagline 内联到同一行 */}
              <span
                className={cn(
                  'w-1.5 h-1.5 rounded-full shrink-0 ml-1',
                  connected
                    ? 'bg-tertiary-fixed animate-pulse'
                    : connecting
                      ? 'bg-tertiary-fixed-dim animate-pulse'
                      : 'bg-outline',
                )}
              />
              <span className="font-mono text-label-mono text-tertiary-fixed-dim uppercase truncate hidden sm:inline">
                {hydrated
                  ? persona.tagline
                  : connected
                    ? '上行链路激活'
                    : '上行链路待激活'}
              </span>
            </button>
          </div>
          <Link
            href="/ask/voice"
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 bg-primary text-on-primary font-mono text-label-mono uppercase tracking-widest hover:bg-primary/90 transition-colors active:scale-95 shrink-0"
          >
            <Phone size={12} />
            <span className="hidden sm:inline">语音通话</span>
          </Link>
        </div>
      </header>

      {/* 对话流 */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto min-h-0 spatial-grid"
      >
        <div className="mx-auto max-w-chat px-margin-mobile md:px-margin-desktop py-grid-major space-y-grid-major relative z-10">
          {/* 时间戳分隔符 */}
          <div className="flex justify-center">
            <span className="font-mono text-label-mono text-outline px-3 py-1 border border-outline-variant bg-black uppercase tracking-widest">
              会话开始_T+00:00:01
            </span>
          </div>

          {chatMessages.map((m, i) => (
            <MessageBubble
              key={i}
              msg={m}
              index={i}
              streaming={
                streaming &&
                i === chatMessages.length - 1 &&
                (m.kind === 'assistant' || m.kind === 'clarify')
              }
              onFollowUp={askAgain}
              onRetry={() => retryLast(i)}
              disabled={streaming || connecting}
            />
          ))}

          {/* 思考中指示器 — 仅在首个 reasoning/content 到达前显示 */}
          {waitingFirstToken && (
            <div className="flex items-center gap-2 text-outline font-mono text-label-mono animate-pulse">
              <span>AI 正在思考</span>
              <span className="flex gap-1">
                <span className="w-1 h-1 bg-outline rounded-full" />
                <span className="w-1 h-1 bg-outline rounded-full" />
                <span className="w-1 h-1 bg-outline rounded-full" />
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 输入栏 */}
      <footer className="border-t border-outline-variant bg-black z-40">
        <div className="mx-auto max-w-chat px-margin-mobile md:px-margin-desktop py-4">
          <div className="flex items-center justify-between mb-2">
            <span
              className={cn(
                'font-mono text-label-mono uppercase tracking-widest transition-colors',
                focused ? 'text-primary' : 'text-outline',
              )}
            >
              {focused
                ? '输入缓冲区：激活传输中'
                : connecting
                  ? '建立会话中…'
                  : '输入缓冲区：就绪'}
            </span>
            <span className="font-mono text-label-mono text-primary uppercase tracking-widest flex items-center gap-3">
              {remaining !== null && (
                <span className="text-tertiary-fixed">剩余 {remaining} 次</span>
              )}
              <span>{connected ? '链路: 在线' : '链路: 离线'}</span>
            </span>
          </div>

          <div className="flex items-end gap-2 border border-outline focus-within:border-primary transition-colors bg-surface-container-lowest">
            <button
              className="w-12 h-12 flex items-center justify-center text-outline hover:text-primary transition-colors shrink-0"
              aria-label="附加"
            >
              <Plus size={18} />
            </button>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit();
                }
              }}
              placeholder="发送消息…"
              rows={1}
              disabled={streaming || connecting}
              className="flex-1 bg-transparent border-none focus:outline-none py-3 font-mono text-body-sm text-on-surface placeholder:text-outline resize-none disabled:opacity-50 min-w-0"
            />
            <button
              className="w-12 h-12 flex items-center justify-center text-outline hover:text-primary transition-colors shrink-0"
              aria-label="语音输入"
            >
              <Mic size={18} />
            </button>
            {streaming ? (
              <button
                onClick={stop}
                className="w-12 h-12 bg-error flex items-center justify-center active:scale-95 transition-transform shrink-0"
                aria-label="停止生成"
              >
                <Square size={14} className="text-on-error" fill="currentColor" />
              </button>
            ) : (
              <button
                onClick={() => onSubmit()}
                disabled={connecting || !input.trim()}
                className="w-12 h-12 bg-primary flex items-center justify-center active:scale-95 transition-transform disabled:opacity-50 shrink-0"
                aria-label="发送"
              >
                <Send size={16} className="text-on-primary" />
              </button>
            )}
          </div>

          {/* 快捷命令 */}
          <div className="flex gap-2 mt-3 overflow-x-auto items-center">
            {quickCommands.map((cmd) => (
              <button
                key={cmd}
                onClick={() => onSubmit(cmd)}
                disabled={streaming || connecting}
                className="px-3 py-1.5 border border-outline-variant font-mono text-label-mono text-on-surface-variant whitespace-nowrap hover:border-primary hover:text-primary transition-colors disabled:opacity-50"
              >
                {cmd}
              </button>
            ))}
            <span className="ml-auto px-3 py-1.5 font-mono text-label-mono text-outline uppercase tracking-widest whitespace-nowrap hidden sm:block">
              AES-256 已加密
            </span>
          </div>
        </div>
      </footer>

      {/* 角色切换 Drawer — 快速切换不离开对话页 */}
      <Drawer
        open={personaDrawerOpen}
        onClose={() => setPersonaDrawerOpen(false)}
        placement="right"
        width={320}
        title={
          <span className="font-mono text-label-mono text-primary uppercase tracking-widest">
            身份选择协议
          </span>
        }
        styles={{
          header: { borderBottomColor: '#1a1a1a', background: '#0a0a0a' },
          body: { padding: 0, background: '#0a0a0a' },
        }}
      >
        <div className="flex flex-col">
          {personas.map((p) => {
            const active = hydrated && p.id === personaId;
            return (
              <button
                key={p.id}
                onClick={() => {
                  select(p.id);
                  setPersonaDrawerOpen(false);
                }}
                className={cn(
                  'flex items-start gap-3 px-5 py-4 border-b border-outline-variant text-left transition-colors',
                  active
                    ? 'bg-surface-container-lowest'
                    : 'hover:bg-surface-container-lowest',
                )}
              >
                <div
                  className={cn(
                    'w-8 h-8 border flex items-center justify-center shrink-0 font-mono text-label-mono',
                    active
                      ? 'border-tertiary-fixed text-tertiary-fixed bg-tertiary-fixed/10'
                      : 'border-outline-variant text-on-surface-variant',
                  )}
                >
                  {p.serial}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={cn(
                        'font-headline text-body-md',
                        active ? 'text-primary' : 'text-on-surface',
                      )}
                    >
                      {p.name}
                    </span>
                    {active && (
                      <Check size={14} className="text-tertiary-fixed shrink-0" />
                    )}
                  </div>
                  <span className="font-mono text-label-mono text-tertiary-fixed-dim uppercase tracking-widest">
                    {p.tagline}
                  </span>
                  <p className="font-sans text-body-sm text-on-surface-variant mt-1 line-clamp-2">
                    {p.description}
                  </p>
                </div>
              </button>
            );
          })}
          <Link
            href="/ask/persona"
            onClick={() => setPersonaDrawerOpen(false)}
            className="px-5 py-4 font-mono text-label-mono text-on-surface-variant hover:text-primary hover:bg-surface-container-lowest uppercase tracking-widest transition-colors"
          >
            查看完整角色档案 →
          </Link>
        </div>
      </Drawer>
    </div>
  );
}

// ===== 消息气泡 =====

/**
 * 思考过程折叠区（reasoning 模型专用）。
 * - 流式思考中（streaming=true）：自动展开，显示光标，不可手动收起
 * - 思考完成（streaming=false）：自动收起，显示字数统计，可手动展开/收起
 */
function ReasoningBlock({
  reasoning,
  streaming,
}: {
  reasoning: string;
  streaming: boolean;
}) {
  const [expanded, setExpanded] = useState(streaming);

  // streaming 变化时同步：思考中展开，完成收起
  useEffect(() => {
    setExpanded(streaming);
  }, [streaming]);

  return (
    <div className="mb-4 border-l-2 border-tertiary-fixed/40 pl-3">
      <button
        type="button"
        disabled={streaming}
        onClick={() => !streaming && setExpanded(!expanded)}
        className="flex items-center gap-2 font-mono text-label-mono text-on-surface-variant hover:text-tertiary-fixed transition-colors w-full disabled:cursor-default"
      >
        <Brain
          size={12}
          className={cn(streaming ? 'text-tertiary-fixed animate-pulse' : '')}
        />
        <span className="uppercase tracking-widest">
          {streaming ? '思考中' : '思考过程'}
        </span>
        {!streaming && (
          <span className="text-outline">· {reasoning.length} 字</span>
        )}
        {!streaming && (
          <ChevronDown
            size={12}
            className={cn('ml-auto transition-transform', expanded && 'rotate-180')}
          />
        )}
      </button>
      {expanded && (
        <div className="mt-2 font-mono text-body-sm text-on-surface-variant/70 leading-relaxed whitespace-pre-wrap max-h-80 overflow-y-auto">
          {reasoning}
          {streaming && <span className="cursor-blink" />}
        </div>
      )}
    </div>
  );
}

function MessageBubble({
  msg,
  index,
  streaming,
  onFollowUp,
  onRetry,
  disabled,
}: {
  msg: ChatMsg;
  index: number;
  streaming: boolean;
  onFollowUp: (text: string) => void;
  onRetry: () => void;
  disabled: boolean;
}) {
  if (msg.kind === 'user') {
    return (
      <div className="flex flex-col items-end">
        <div className="w-fit max-w-full">
          <div className="font-mono text-label-mono text-outline mb-2 flex justify-end gap-4 uppercase tracking-widest">
            <span>{msg.timestamp || '——'}</span>
            <span>操作员</span>
          </div>
          {/* 用户气泡：secondary-container（中深灰）与模型气泡（surface-container-lowest，最深）形成层次区分，
              避免纯白背景在深色主题下过于刺眼。msg-user-bubble 用于覆盖 ::selection。 */}
          <div className="msg-user-bubble bg-secondary-container text-on-secondary-container border border-outline-variant p-4 md:p-6">
            <p className="font-sans text-body-md leading-relaxed whitespace-pre-wrap">
              {msg.content}
            </p>
            {/* 用户消息底部操作栏：仅复制 */}
            {!streaming && (
              <div className="flex justify-end">
                <MessageActions content={msg.content} compact />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (msg.kind === 'error') {
    return (
      <div className="flex flex-col items-start max-w-[85%] md:max-w-[70%]">
        <div className="font-mono text-label-mono text-outline mb-2 flex gap-4 uppercase tracking-widest">
          <span>AI 节点</span>
          <span>{msg.timestamp || '——'}</span>
        </div>
        <div className="border border-error/60 bg-error-container/20 p-4 md:p-6 w-full flex items-start gap-3">
          <AlertCircle size={16} className="text-error shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="font-mono text-label-mono text-error uppercase tracking-widest mb-1">
              错误 {msg.code ? `· ${msg.code}` : ''}
            </p>
            <p className="font-sans text-body-sm text-on-surface leading-relaxed">
              {msg.content}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (msg.kind === 'clarify') {
    return (
      <div className="flex flex-col items-start max-w-[85%] md:max-w-[70%]">
        <div className="font-mono text-label-mono text-outline mb-2 flex gap-4 uppercase tracking-widest">
          <span>AI 节点</span>
          <span>{msg.timestamp || '——'}</span>
        </div>
        <div
          className="bg-surface-container-lowest border border-outline-variant p-4 md:p-6 w-full"
          style={{ borderTopColor: 'rgba(255,255,255,0.1)' }}
        >
          <p className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest mb-2">
            需要澄清
          </p>
          <p className="font-sans text-body-md text-on-surface leading-relaxed whitespace-pre-wrap">
            {msg.content}
          </p>
          {msg.options && msg.options.length > 0 && (
            <div className="mt-4 flex flex-col gap-2">
              {msg.options.map((opt, i) => (
                <button
                  key={i}
                  disabled={disabled}
                  onClick={() => onFollowUp(opt)}
                  className="text-left px-3 py-2 border border-outline-variant font-sans text-body-sm text-on-surface-variant hover:border-tertiary-fixed hover:text-tertiary-fixed transition-colors disabled:opacity-50"
                >
                  <span className="font-mono text-label-mono text-tertiary-fixed mr-2">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  {opt}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // assistant
  return (
    <div className="flex flex-col items-start w-fit max-w-full">
      <div className="font-mono text-label-mono text-outline mb-2 flex gap-4 uppercase tracking-widest">
        <span>AI 节点</span>
        <span>{msg.timestamp || '——'}</span>
      </div>
      {/* inner-glow: 1px top border 替代阴影，表达层级抬升 */}
      <div
        className="bg-surface-container-lowest border border-outline-variant p-4 md:p-6 w-full"
        style={{ borderTopColor: 'rgba(255,255,255,0.1)' }}
      >
        {/* 思考过程折叠区（reasoning 模型） */}
        {msg.reasoning && (
          <ReasoningBlock
            reasoning={msg.reasoning}
            streaming={!!msg.reasoningStreaming}
          />
        )}
        {/* 正式回答（content 为空且仍在思考时隐藏，避免空气泡） */}
        {(msg.content || !msg.reasoning) && (
          <div className="text-on-surface leading-relaxed">
            <ChatMarkdown content={msg.content} />
            {streaming && msg.streaming && <span className="cursor-blink" />}
          </div>
        )}

        {/* 引用溯源 */}
        {msg.citations && msg.citations.length > 0 && (
          <div className="mt-4 border-t border-outline-variant pt-4">
            <p className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <FileText size={12} />
              引用出处 · {msg.citations.length}
            </p>
            <ul className="space-y-2">
              {msg.citations.map((c, i) => (
                <li key={c.articleId + i}>
                  {c.slug ? (
                    <Link
                      href={`/posts/${c.slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-start gap-2 px-2 py-1.5 -mx-2 hover:bg-surface-container-low transition-colors"
                    >
                      <span className="font-mono text-label-mono text-tertiary-fixed mt-0.5 shrink-0">
                        [{i + 1}]
                      </span>
                      <span className="flex-1 min-w-0">
                        <span className="font-sans text-body-sm text-on-surface group-hover:text-primary transition-colors block truncate">
                          {c.title || c.slug}
                        </span>
                        {c.snippet && (
                          <span className="font-mono text-label-mono text-on-surface-variant line-clamp-2 mt-0.5">
                            {c.snippet}
                          </span>
                        )}
                      </span>
                    </Link>
                  ) : (
                    <div className="flex items-start gap-2 px-2 py-1.5 -mx-2">
                      <span className="font-mono text-label-mono text-tertiary-fixed mt-0.5 shrink-0">
                        [{i + 1}]
                      </span>
                      <span className="flex-1 min-w-0">
                        <span className="font-sans text-body-sm text-on-surface block truncate">
                          {c.title}
                        </span>
                        {c.snippet && (
                          <span className="font-mono text-label-mono text-on-surface-variant line-clamp-2 mt-0.5">
                            {c.snippet}
                          </span>
                        )}
                      </span>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 追问建议 */}
        {msg.followUps && msg.followUps.length > 0 && !streaming && (
          <div className="mt-4 flex flex-wrap gap-2">
            {msg.followUps.map((q, i) => (
              <button
                key={i}
                disabled={disabled}
                onClick={() => onFollowUp(q)}
                className="px-3 py-1.5 border border-outline-variant font-sans text-body-sm text-on-surface-variant hover:border-tertiary-fixed hover:text-tertiary-fixed transition-colors disabled:opacity-50 text-left"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* 操作栏：复制 / 重试 / 点赞 / 点踩（流式结束后显示） */}
        {!streaming && msg.content && (
          <MessageActions content={msg.content} onRetry={onRetry} />
        )}
      </div>
    </div>
  );
}
