'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import type { Citation } from '@/types';

/**
 * useChat — /ws/chat 文字流式问答客户端。
 *
 * 后端协议（app/schemas/ws.py）：
 *   C→S: user_message / stop / heartbeat
 *   S→C: token / citation / followup / clarify / done / error / rate
 *
 * 会话懒创建：首次 send 时若本地无 sessionId，先 POST /api/chat/sessions
 * 拿到 id 后建立 WS 连接；连接复用至组件卸载或会话切换。
 *
 * 重连策略：非主动关闭的断开按 1s/2s/4s 指数退避重试 3 次。
 * 心跳：每 30s 发一帧 heartbeat，避免反向代理断开空闲连接。
 */

// ===== 帧类型常量（与后端 app/schemas/ws.py 对齐）=====
const FT = {
  USER_MESSAGE: 'user_message',
  STOP: 'stop',
  HEARTBEAT: 'heartbeat',
  TOKEN: 'token',
  REASONING: 'reasoning',
  CITATION: 'citation',
  FOLLOWUP: 'followup',
  CLARIFY: 'clarify',
  DONE: 'done',
  ERROR: 'error',
  RATE: 'rate',
} as const;

// ===== 消息类型 =====

export type ChatMsg =
  | {
      kind: 'user';
      content: string;
      timestamp: string;
    }
  | {
      kind: 'assistant';
      content: string;
      citations?: Citation[];
      followUps?: string[];
      timestamp: string;
      /** 是否仍在流式接收中（用于渲染光标） */
      streaming?: boolean;
      /** reasoning 模型的思考过程（流式增量拼接） */
      reasoning?: string;
      /** 思考是否仍在进行 — true 时 UI 展开思考区，false 时自动收起（可手动展开） */
      reasoningStreaming?: boolean;
    }
  | {
      kind: 'clarify';
      content: string;
      options?: string[];
      timestamp: string;
    }
  | {
      kind: 'error';
      content: string;
      code?: string;
      timestamp: string;
    };

export interface UseChatOptions {
  personaId?: string | null;
  scopeType?: 'global' | 'channel' | 'article';
  scopeRef?: string | null;
  /** 初始消息（如欢迎语） */
  initialMessages?: ChatMsg[];
}

export interface UseChatReturn {
  messages: ChatMsg[];
  streaming: boolean;
  connected: boolean;
  remaining: number | null;
  /** 会话尚未建立 / 正在建立中 */
  connecting: boolean;
  send: (text: string) => void;
  stop: () => void;
  reset: () => void;
}

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_BASE || 'ws://localhost:8000';
const HEARTBEAT_MS = 30_000;
const MAX_RETRIES = 3;

export function useChat(opts: UseChatOptions = {}): UseChatReturn {
  const { personaId, scopeType = 'global', scopeRef, initialMessages = [] } = opts;

  const [messages, setMessages] = useState<ChatMsg[]>(initialMessages);
  const [streaming, setStreaming] = useState(false);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);

  // refs：避免重连/重渲染时丢失 WS 与定时器
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);
  // 待发送队列：session 建立期间用户提交的问题先缓存
  const pendingSendRef = useRef<string | null>(null);
  // 最新 personaId/scope，供 ensureSession 读取
  const personaIdRef = useRef(personaId);
  const scopeRefRef = useRef(scopeRef);
  const scopeTypeRef = useRef(scopeType);
  useEffect(() => {
    personaIdRef.current = personaId;
  }, [personaId]);
  useEffect(() => {
    scopeRefRef.current = scopeRef;
    scopeTypeRef.current = scopeType;
  }, [scopeRef, scopeType]);

  // ===== 清理 =====
  const clearTimers = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  const closeSocket = useCallback(() => {
    intentionalCloseRef.current = true;
    clearTimers();
    const ws = wsRef.current;
    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      try {
        ws.close();
      } catch {
        /* noop */
      }
      wsRef.current = null;
    }
    setConnected(false);
  }, [clearTimers]);

  // ===== 帧处理 =====
  const handleFrame = useCallback((data: unknown) => {
    const frame = data as { type?: string; [k: string]: unknown };
    if (!frame || typeof frame.type !== 'string') return;

    switch (frame.type) {
      case FT.TOKEN: {
        const content = (frame.content as string) || '';
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.kind === 'assistant' && last.streaming) {
            // 追加到当前流式消息；若之前在思考，标记思考结束（UI 自动收起思考区）
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + content, reasoningStreaming: false },
            ];
          }
          // 新开一条流式 assistant 消息
          return [
            ...prev,
            {
              kind: 'assistant',
              content,
              streaming: true,
              timestamp: nowTime(),
            },
          ];
        });
        break;
      }
      case FT.REASONING: {
        const content = (frame.content as string) || '';
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.kind === 'assistant' && last.streaming) {
            // 追加到当前消息的思考区
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                reasoning: (last.reasoning || '') + content,
                reasoningStreaming: true,
              },
            ];
          }
          // reasoning 先于 token 到达：新建一条 assistant 消息（content 暂空）
          return [
            ...prev,
            {
              kind: 'assistant',
              content: '',
              reasoning: content,
              reasoningStreaming: true,
              streaming: true,
              timestamp: nowTime(),
            },
          ];
        });
        break;
      }
      case FT.CITATION: {
        const citations = (frame.data as Citation[]) || [];
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.kind === 'assistant') {
            return [
              ...prev.slice(0, -1),
              { ...last, citations },
            ];
          }
          return prev;
        });
        break;
      }
      case FT.FOLLOWUP: {
        const questions = (frame.questions as string[]) || [];
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.kind === 'assistant') {
            return [
              ...prev.slice(0, -1),
              { ...last, followUps: questions },
            ];
          }
          return prev;
        });
        break;
      }
      case FT.CLARIFY: {
        const content = (frame.content as string) || '';
        const options = frame.options as string[] | undefined;
        // clarify 替换当前 streaming 占位（如果有），否则新增
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.kind === 'assistant' && last.streaming) {
            return [
              ...prev.slice(0, -1),
              { kind: 'clarify', content, options, timestamp: nowTime() },
            ];
          }
          return [
            ...prev,
            { kind: 'clarify', content, options, timestamp: nowTime() },
          ];
        });
        setStreaming(false);
        break;
      }
      case FT.DONE: {
        // 结束当前流式消息的 streaming 标记
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.kind === 'assistant' && last.streaming) {
            return [...prev.slice(0, -1), { ...last, streaming: false }];
          }
          return prev;
        });
        setStreaming(false);
        break;
      }
      case FT.ERROR: {
        const message = (frame.message as string) || '回答生成失败';
        const code = frame.code as string | undefined;
        setMessages((prev) => {
          // 替换当前空 streaming 占位，避免留下空气泡
          const last = prev[prev.length - 1];
          if (last && last.kind === 'assistant' && last.streaming && last.content === '') {
            return [
              ...prev.slice(0, -1),
              { kind: 'error', content: message, code, timestamp: nowTime() },
            ];
          }
          return [...prev, { kind: 'error', content: message, code, timestamp: nowTime() }];
        });
        setStreaming(false);
        break;
      }
      case FT.RATE: {
        const r = frame.remaining;
        if (typeof r === 'number') setRemaining(r);
        break;
      }
      default:
        // 未知帧忽略
        break;
    }
  }, []);

  // ===== 建立连接 =====
  const connect = useCallback(
    (sessionId: string, anonId: string | null) => {
      intentionalCloseRef.current = false;
      retryCountRef.current = 0;

      const url = new URL(`${WS_BASE}/ws/chat`);
      url.searchParams.set('session', sessionId);
      if (anonId) url.searchParams.set('anon_id', anonId);

      const ws = new WebSocket(url.toString());
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryCountRef.current = 0;
        // 心跳
        heartbeatTimerRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: FT.HEARTBEAT }));
          }
        }, HEARTBEAT_MS);
        // flush 待发送消息
        if (pendingSendRef.current) {
          const text = pendingSendRef.current;
          pendingSendRef.current = null;
          ws.send(JSON.stringify({ type: FT.USER_MESSAGE, content: text }));
        }
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          handleFrame(data);
        } catch {
          /* 忽略非法 JSON */
        }
      };

      ws.onerror = () => {
        // 错误后通常紧跟 onclose，由 close 处理重连
      };

      ws.onclose = () => {
        setConnected(false);
        if (heartbeatTimerRef.current) {
          clearInterval(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }
        // 主动关闭不重连
        if (intentionalCloseRef.current) return;
        // 流式中断不自动重连（避免幻觉续写）
        if (streaming) {
          setStreaming(false);
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.kind === 'assistant' && last.streaming) {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  streaming: false,
                  content: last.content + '\n\n[连接中断]',
                },
              ];
            }
            return prev;
          });
          return;
        }
        // 指数退避重连
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = 2 ** retryCountRef.current * 1000;
          retryCountRef.current += 1;
          retryTimerRef.current = setTimeout(() => {
            if (sessionIdRef.current) {
              const anonId = getAnonId();
              connect(sessionIdRef.current, anonId);
            }
          }, delay);
        }
      };
    },
    [handleFrame, streaming],
  );

  // ===== 懒创建 session =====
  const ensureSession = useCallback(async (): Promise<{
    sessionId: string;
    anonId: string | null;
  } | null> => {
    if (sessionIdRef.current) {
      return { sessionId: sessionIdRef.current, anonId: getAnonId() };
    }
    setConnecting(true);
    try {
      // 先确保 anon_session_id 存在，axios interceptor 才能带 X-Session-Id header
      ensureAnonId();
      const s = await api.createChatSession({
        persona_id: personaIdRef.current ?? undefined,
        scope_type: scopeTypeRef.current,
        scope_ref: scopeRefRef.current ?? undefined,
      });
      sessionIdRef.current = s.id;
      return { sessionId: s.id, anonId: getAnonId() };
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          kind: 'error',
          content: '会话建立失败，请稍后重试',
          timestamp: nowTime(),
        },
      ]);
      return null;
    } finally {
      setConnecting(false);
    }
  }, []);

  // ===== send =====
  const send = useCallback(
    (text: string) => {
      const q = text.trim();
      if (!q || streaming || connecting) return;

      // 立即上屏用户消息
      setMessages((prev) => [
        ...prev,
        { kind: 'user', content: q, timestamp: nowTime() },
      ]);
      setStreaming(true);

      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN && sessionIdRef.current) {
        ws.send(JSON.stringify({ type: FT.USER_MESSAGE, content: q }));
        return;
      }

      // 连接未就绪：先建 session + 连接，pending 队列暂存
      pendingSendRef.current = q;
      void ensureSession().then((res) => {
        if (!res) {
          setStreaming(false);
          return;
        }
        // 已有连接且打开：直接发
        const cur = wsRef.current;
        if (cur && cur.readyState === WebSocket.OPEN) {
          // ensureSession 之前可能已 connect，onopen 会 flush pending
          // 这里 double-check 避免重复
          if (pendingSendRef.current) {
            cur.send(
              JSON.stringify({
                type: FT.USER_MESSAGE,
                content: pendingSendRef.current,
              }),
            );
            pendingSendRef.current = null;
          }
          return;
        }
        connect(res.sessionId, res.anonId);
      });
    },
    [streaming, connecting, ensureSession, connect],
  );

  // ===== stop =====
  const stop = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: FT.STOP }));
    }
    setStreaming(false);
    // 立即结束 streaming 标记，不等 done 帧
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.kind === 'assistant' && last.streaming) {
        return [...prev.slice(0, -1), { ...last, streaming: false }];
      }
      return prev;
    });
  }, []);

  // ===== reset =====
  const reset = useCallback(() => {
    setMessages([]);
    setStreaming(false);
    setRemaining(null);
  }, []);

  // ===== persona 变更时切换会话 =====
  useEffect(() => {
    // persona 切换需要新会话，断开旧连接，下次 send 时重建
    if (sessionIdRef.current) {
      closeSocket();
      sessionIdRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  // ===== mount 后补设初始消息的空 timestamp（避免 SSR/CSR 时间不一致）=====
  useEffect(() => {
    setMessages((prev) => {
      if (!prev.some((m) => !m.timestamp)) return prev;
      const t = nowTime();
      return prev.map((m) => (!m.timestamp ? { ...m, timestamp: t } : m));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ===== 卸载清理 =====
  useEffect(() => {
    return () => {
      closeSocket();
    };
  }, [closeSocket]);

  return {
    messages,
    streaming,
    connected,
    connecting,
    remaining,
    send,
    stop,
    reset,
  };
}

// ===== 工具 =====

function nowTime(): string {
  const d = new Date();
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function getAnonId(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('anon_session_id');
}

function ensureAnonId(): string {
  if (typeof window === 'undefined') return '';
  let id = localStorage.getItem('anon_session_id');
  if (!id) {
    id = generateAnonId();
    localStorage.setItem('anon_session_id', id);
  }
  return id;
}

function generateAnonId(): string {
  // 与后端 anon_id 兼容：UUID v4 风格
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'anon-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
}
