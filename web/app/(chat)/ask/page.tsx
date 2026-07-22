'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Drawer } from 'antd';
import { ArrowLeft, Mic, Send, Plus, Phone, User, ChevronDown, Check } from 'lucide-react';
import { usePersona } from '@/lib/usePersona';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  citation?: string;
  timestamp: string;
}

const quickCommands = ['/状态报告', '/知识库概览', '/最新文章', '/清空会话'];

function nowTime() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(
    d.getMinutes(),
  ).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
}

/**
 * AI 对话页 — 终端式沉浸聊天 UI。
 * 参考 plan/虚拟对话.html + plan/虚拟对话-2.html：
 *  - 顶部实体头（状态指示 + 语音通话）
 *  - 时间戳分隔符
 *  - Agent 气泡（surface-container-lowest + 1px 边框 + inner-glow）
 *  - 用户气泡（纯白底 + 黑字）
 *  - 思考中指示器
 *  - 流式光标
 *  - 自动伸缩 textarea + 快捷命令
 *  - 移动端 max-w-md 单列，桌面端 max-w-chat 居中
 */
export default function AskPage() {
  // 初始消息的 timestamp 留空，避免 SSR 与 hydration 时间不一致导致
  // "Text content does not match server-rendered HTML" 错误。真实时间在
  // useEffect 中设置。
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: 'assistant',
      content:
        '上行链路已建立。我基于博主的文章知识库回答你的问题——每一次回答都会标注引用出处。请发送指令或提问。',
      timestamp: '',
    },
  ]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [focused, setFocused] = useState(false);
  const [personaDrawerOpen, setPersonaDrawerOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { persona, personaId, personas, select, hydrated } = usePersona();

  // hydration 完成后补设初始消息的时间戳
  useEffect(() => {
    setMessages((prev) =>
      prev.length > 0 && prev[0].timestamp === ''
        ? [{ ...prev[0], timestamp: nowTime() }, ...prev.slice(1)]
        : prev,
    );
  }, []);

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
  }, [messages, streaming]);

  // textarea 自动伸缩
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  }, [input]);

  const send = (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || streaming) return;
    setMessages((m) => [
      ...m,
      { role: 'user', content: q, timestamp: nowTime() },
    ]);
    setInput('');
    setStreaming(true);
    // 骨架阶段 mock 流式回复，接入 WebSocket 后逐字渲染
    setTimeout(() => {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: `（mock 回复）关于「${q}」，根据博主的文章，可以这样理解……\n\n后续接入流式 WebSocket 后，这里会逐字渲染，并附上引用出处。`,
          citation: '《相关文章》',
          timestamp: nowTime(),
        },
      ]);
      setStreaming(false);
    }, 900);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] min-h-0">
      {/* 实体头 — 角色切换 + 状态指示 + 语音通话 */}
      <header className="border-b border-outline-variant bg-black/70 backdrop-blur-md z-40">
        <div className="mx-auto max-w-chat px-margin-mobile md:px-margin-desktop py-4 flex justify-between items-center gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => {
                if (window.history.length > 1) window.history.back();
                else window.location.href = '/';
              }}
              className="p-2 -ml-2 text-on-surface-variant hover:text-primary transition-colors shrink-0"
              aria-label="返回"
            >
              <ArrowLeft size={18} />
            </button>
            <div className="w-10 h-10 border border-outline bg-surface-container flex items-center justify-center shrink-0">
              <User size={18} className="text-primary" />
            </div>
            {/* 角色切换按钮 — 点击打开 Drawer */}
            <button
              onClick={() => setPersonaDrawerOpen(true)}
              className="flex flex-col min-w-0 text-left group"
              aria-label="切换角色"
            >
              <span className="flex items-center gap-1.5">
                <span className="font-headline text-headline-md text-primary uppercase tracking-tighter leading-none truncate">
                  {hydrated ? persona.name : 'AI 节点'}
                </span>
                <ChevronDown
                  size={14}
                  className="text-on-surface-variant group-hover:text-primary transition-colors shrink-0"
                />
              </span>
              <span className="font-mono text-label-mono text-tertiary-fixed-dim uppercase flex items-center gap-2 mt-1.5">
                <span className="w-1.5 h-1.5 bg-tertiary-fixed-dim animate-pulse" />
                {hydrated ? persona.tagline : '上行链路激活'}
              </span>
            </button>
          </div>
          <Link
            href="/ask/voice"
            className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-primary text-on-primary font-mono text-label-mono uppercase tracking-widest hover:bg-primary/90 transition-colors active:scale-95 shrink-0"
          >
            <Phone size={14} />
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

          {messages.map((m, i) => (
            <MessageBubble
              key={i}
              msg={m}
              streaming={
                streaming &&
                i === messages.length - 1 &&
                m.role === 'assistant'
              }
            />
          ))}

          {/* 思考中指示器 */}
          {streaming && (
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
              className={`font-mono text-label-mono uppercase tracking-widest transition-colors ${
                focused ? 'text-primary' : 'text-outline'
              }`}
            >
              {focused ? '输入缓冲区：激活传输中' : '输入缓冲区：就绪'}
            </span>
            <span className="font-mono text-label-mono text-primary uppercase tracking-widest">
              延迟: 12ms
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
                  send();
                }
              }}
              placeholder="发送消息…"
              rows={1}
              disabled={streaming}
              className="flex-1 bg-transparent border-none focus:outline-none py-3 font-mono text-body-sm text-on-surface placeholder:text-outline resize-none disabled:opacity-50 min-w-0"
            />
            <button
              className="w-12 h-12 flex items-center justify-center text-outline hover:text-primary transition-colors shrink-0"
              aria-label="语音输入"
            >
              <Mic size={18} />
            </button>
            <button
              onClick={() => send()}
              disabled={streaming}
              className="w-12 h-12 bg-primary flex items-center justify-center active:scale-95 transition-transform disabled:opacity-50 shrink-0"
              aria-label="发送"
            >
              <Send size={16} className="text-on-primary" />
            </button>
          </div>

          {/* 快捷命令 */}
          <div className="flex gap-2 mt-3 overflow-x-auto items-center">
            {quickCommands.map((cmd) => (
              <button
                key={cmd}
                onClick={() => send(cmd)}
                className="px-3 py-1.5 border border-outline-variant font-mono text-label-mono text-on-surface-variant whitespace-nowrap hover:border-primary hover:text-primary transition-colors"
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
                className={`flex items-start gap-3 px-5 py-4 border-b border-outline-variant text-left transition-colors ${
                  active ? 'bg-surface-container-lowest' : 'hover:bg-surface-container-lowest'
                }`}
              >
                <div
                  className={`w-8 h-8 border flex items-center justify-center shrink-0 font-mono text-label-mono ${
                    active
                      ? 'border-tertiary-fixed text-tertiary-fixed bg-tertiary-fixed/10'
                      : 'border-outline-variant text-on-surface-variant'
                  }`}
                >
                  {p.serial}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`font-headline text-body-md ${
                        active ? 'text-primary' : 'text-on-surface'
                      }`}
                    >
                      {p.name}
                    </span>
                    {active && <Check size={14} className="text-tertiary-fixed shrink-0" />}
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

function MessageBubble({ msg, streaming }: { msg: Msg; streaming: boolean }) {
  if (msg.role === 'user') {
    return (
      <div className="flex flex-col items-end">
        <div className="max-w-[85%] md:max-w-[70%] w-full">
          <div className="font-mono text-label-mono text-outline mb-2 flex justify-end gap-4 uppercase tracking-widest">
            <span>{msg.timestamp}</span>
            <span>操作员</span>
          </div>
          <div className="bg-primary text-on-primary p-4 md:p-6">
            <p className="font-sans text-body-md leading-relaxed whitespace-pre-wrap">
              {msg.content}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start max-w-[85%] md:max-w-[70%]">
      <div className="font-mono text-label-mono text-outline mb-2 flex gap-4 uppercase tracking-widest">
        <span>AI 节点</span>
        <span>{msg.timestamp}</span>
      </div>
      {/* inner-glow: 1px top border 替代阴影，表达层级抬升 */}
      <div
        className="bg-surface-container-lowest border border-outline-variant p-4 md:p-6 w-full"
        style={{ borderTopColor: 'rgba(255,255,255,0.1)' }}
      >
        <p className="font-sans text-body-md text-on-surface leading-relaxed whitespace-pre-wrap">
          {msg.content}
          {streaming && <span className="cursor-blink" />}
        </p>
        {msg.citation && (
          <p className="mt-3 font-mono text-label-mono text-on-surface-variant border-t border-outline-variant pt-3 uppercase tracking-widest">
            引用 → {msg.citation}
          </p>
        )}
      </div>
    </div>
  );
}
