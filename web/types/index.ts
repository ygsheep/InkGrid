/**
 * 全局类型定义
 */

/** 文章摘要/列表项 */
export interface ArticleSummary {
  id: string;
  slug: string;
  title: string;
  excerpt: string; // 副标题/摘要一行
  channel: string; // 频道 slug
  channelName: string;
  tags?: string[];
  publishedAt: string; // ISO 日期
  readingTime?: number; // 分钟
}

/** 文章详情 */
export interface Article extends ArticleSummary {
  content: string; // Markdown 源码
  html?: string; // 预渲染 HTML（可选）
  toc?: TocItem[];
}

export interface TocItem {
  id: string;
  title: string;
  level: number;
}

/** 频道 */
export interface Channel {
  slug: string;
  name: string;
  description: string;
  persona?: string; // 人设提示
  accent?: 'channel' | 'policy';
  postCount?: number;
}

/** AI 对话角色（人设） */
export interface Persona {
  id: string;
  /** 序号，如 "001" */
  serial: string;
  name: string;
  tagline: string;
  description: string;
  /** 标签芯片 */
  tags: string[];
  /** 头像 URL（可为空，使用占位） */
  avatar?: string;
}

/** 问答范围 */
export type ChatScope =
  | { type: 'global' }
  | { type: 'channel'; refId: string }
  | { type: 'article'; refId: string };

/** 引用溯源 */
export interface Citation {
  articleId: string;
  title: string;
  slug: string;
  snippet: string;
}

/** 对话消息 */
export type ChatMessage =
  | { id: string; role: 'user'; content: string; createdAt: string }
  | {
      id: string;
      role: 'assistant';
      content: string;
      citations?: Citation[];
      followUps?: string[];
      createdAt: string;
    }
  | {
      id: string;
      role: 'assistant';
      type: 'clarify';
      content: string;
      options?: string[];
      createdAt: string;
    };

/** 语音通话状态 */
export type VoiceStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'speaking'
  | 'listening'
  | 'ended'
  | 'error';
