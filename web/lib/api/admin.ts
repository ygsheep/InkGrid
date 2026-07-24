/**
 * 后台 admin REST API 封装。
 * 所有路径相对于 NEXT_PUBLIC_API_BASE（dev: http://localhost:8000/api）。
 * cookie admin_token 由浏览器自动携带（withCredentials=true）。
 *
 * 路径前缀：/admin/* 对应后端 app/api/admin/* 路由
 */
import { request } from './request';
import type { Paginated } from './index';

// ===== 类型 =====

export interface AdminInfo {
  id: string;
  username: string;
}

export interface AdminPost {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  content: string;
  html: string | null;
  channel_id: string;
  channel_slug: string | null;
  channel_name: string | null;
  tags: string[] | null;
  status: 'draft' | 'published' | 'archived';
  published_at: string | null;
  reading_time: number | null;
  toc: { id: string; title: string; level: number }[];
  created_at: string | null;
  updated_at: string | null;
}

/** 文章批量上传结果（created 为 AdminPost[]，区别于知识库的 UploadResult）。 */
export interface PostUploadResult {
  created: AdminPost[];
  failed: { filename: string; reason: string }[];
}

export interface AdminChannel {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  accent: string | null;
  persona_id: string | null;
  postCount: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminPersona {
  id: string;
  serial: string;
  name: string;
  tagline: string;
  description: string;
  tags: string[] | null;
  avatar: string | null;
  system_prompt: string;
  scope: string;
}

export interface SiteSettings {
  siteName: string;
  author: string;
  version: string;
  extra: Record<string, unknown>;
}

// ===== unwrap 工具 =====
// response interceptor 已 unwrap envelope，request.get/post 返回的是 data 本身
function unwrap<T>(p: Promise<unknown>): Promise<T> {
  return p as Promise<T>;
}

// ===== Auth =====

export const authApi = {
  login(payload: { username: string; password: string }) {
    return unwrap<AdminInfo>(request.post('/admin/auth/login', payload));
  },
  logout() {
    return unwrap<{ ok: boolean }>(request.post('/admin/auth/logout'));
  },
  me() {
    return unwrap<AdminInfo>(request.get('/admin/auth/me'));
  },
};

// ===== Posts =====

export interface PostListParams {
  status?: string;
  channel_id?: string;
  q?: string;
  page?: number;
  size?: number;
}

export interface PostCreatePayload {
  slug: string;
  title: string;
  excerpt?: string | null;
  content_md: string;
  channel_id: string;
  tags?: string[] | null;
  status?: string;
  reading_time?: number | null;
  toc?: { id: string; title: string; level: number }[] | null;
}

export interface PostUpdatePayload {
  slug?: string;
  title?: string;
  excerpt?: string | null;
  content_md?: string;
  channel_id?: string;
  tags?: string[] | null;
  status?: string;
  reading_time?: number | null;
  toc?: { id: string; title: string; level: number }[] | null;
}

export const postsApi = {
  list(params: PostListParams = {}) {
    const qs = new URLSearchParams();
    if (params.status) qs.set('status', params.status);
    if (params.channel_id) qs.set('channel_id', params.channel_id);
    if (params.q) qs.set('q', params.q);
    if (params.page) qs.set('page', String(params.page));
    if (params.size) qs.set('size', String(params.size));
    return unwrap<Paginated<AdminPost>>(
      request.get(`/admin/posts${qs.toString() ? `?${qs}` : ''}`),
    );
  },
  get(id: string) {
    return unwrap<AdminPost>(request.get(`/admin/posts/${id}`));
  },
  create(payload: PostCreatePayload) {
    return unwrap<AdminPost>(request.post('/admin/posts', payload));
  },
  update(id: string, payload: PostUpdatePayload) {
    return unwrap<AdminPost>(request.patch(`/admin/posts/${id}`, payload));
  },
  remove(id: string) {
    return unwrap<{ ok: boolean }>(request.delete(`/admin/posts/${id}`));
  },
  setStatus(id: string, status: string) {
    return unwrap<AdminPost>(request.post(`/admin/posts/${id}/status`, { status }));
  },
  /**
   * 批量上传 Markdown 文件 → 创建草稿。
   * 多文件时逐文件解析创建，单个失败不阻断其他。
   * 返回 PostUploadResult { created: AdminPost[], failed: UploadFailedItem[] }。
   */
  uploadMd(files: File[], channelId: string) {
    const form = new FormData();
    for (const f of files) {
      form.append('files', f);
    }
    form.append('channel_id', channelId);
    // 多文件解析可能耗时，放宽超时
    return unwrap<PostUploadResult>(
      request.post('/admin/posts/upload', form, {
        timeout: 120000,
      }),
    );
  },
};

// ===== Uploads =====

export interface ImageUploadResult {
  url: string;
  size: number;
  max_size: number;
}

export const uploadsApi = {
  uploadImage(file: File) {
    const form = new FormData();
    form.append('file', file);
    return unwrap<ImageUploadResult>(
      request.post('/admin/uploads/image', form, {
        timeout: 30000,
      }),
    );
  },
};

// ===== Channels =====

export interface ChannelCreatePayload {
  slug: string;
  name: string;
  description?: string | null;
  accent?: string | null;
  persona_id?: string | null;
}

export interface ChannelUpdatePayload {
  slug?: string;
  name?: string;
  description?: string | null;
  accent?: string | null;
  persona_id?: string | null;
}

export const channelsApi = {
  list(params: { page?: number; size?: number } = {}) {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.size) qs.set('size', String(params.size));
    return unwrap<Paginated<AdminChannel>>(
      request.get(`/admin/channels${qs.toString() ? `?${qs}` : ''}`),
    );
  },
  get(id: string) {
    return unwrap<AdminChannel>(request.get(`/admin/channels/${id}`));
  },
  create(payload: ChannelCreatePayload) {
    return unwrap<AdminChannel>(request.post('/admin/channels', payload));
  },
  update(id: string, payload: ChannelUpdatePayload) {
    return unwrap<AdminChannel>(request.patch(`/admin/channels/${id}`, payload));
  },
  remove(id: string) {
    return unwrap<{ ok: boolean }>(request.delete(`/admin/channels/${id}`));
  },
};

// ===== Personas =====

export interface PersonaCreatePayload {
  serial: string;
  name: string;
  tagline: string;
  description: string;
  tags?: string[] | null;
  avatar?: string | null;
  system_prompt: string;
  scope?: string;
}

export interface PersonaUpdatePayload {
  serial?: string;
  name?: string;
  tagline?: string;
  description?: string;
  tags?: string[] | null;
  avatar?: string | null;
  system_prompt?: string;
  scope?: string;
}

export const personasApi = {
  list(params: { scope?: string; page?: number; size?: number } = {}) {
    const qs = new URLSearchParams();
    if (params.scope) qs.set('scope', params.scope);
    if (params.page) qs.set('page', String(params.page));
    if (params.size) qs.set('size', String(params.size));
    return unwrap<Paginated<AdminPersona>>(
      request.get(`/admin/personas${qs.toString() ? `?${qs}` : ''}`),
    );
  },
  get(id: string) {
    return unwrap<AdminPersona>(request.get(`/admin/personas/${id}`));
  },
  create(payload: PersonaCreatePayload) {
    return unwrap<AdminPersona>(request.post('/admin/personas', payload));
  },
  update(id: string, payload: PersonaUpdatePayload) {
    return unwrap<AdminPersona>(request.patch(`/admin/personas/${id}`, payload));
  },
  remove(id: string) {
    return unwrap<{ ok: boolean }>(request.delete(`/admin/personas/${id}`));
  },
};

// ===== Settings =====

export interface SettingsUpdatePayload {
  site_name?: string;
  author?: string;
  version?: string;
  extra?: Record<string, unknown>;
}

export const settingsApi = {
  get() {
    return unwrap<SiteSettings>(request.get('/admin/settings'));
  },
  update(payload: SettingsUpdatePayload) {
    return unwrap<SiteSettings>(request.patch('/admin/settings', payload));
  },
};

// ===== Stats（数据看板）=====

export interface StatsSummary {
  postCount: number;
  questionCount: number;
  knowledgeDocCount: number;
  monthlyViews: number;
}

export interface StatsTrend {
  posts: number[];
  questions: number[];
}

export interface TopArticle {
  slug: string;
  title: string;
  channelName: string | null;
  citationCount: number;
}

export interface TopQuestion {
  content: string;
  count: number;
}

export interface RecentQuestion {
  sessionId: string;
  title: string | null;
  personaName: string | null;
  scopeType: string;
  scopeRef: string | null;
  firstQuestion: string | null;
  lastAnswerSnippet: string | null;
  messageCount: number;
  createdAt: string;
}

export interface StatsOverview {
  summary: StatsSummary;
  trend: StatsTrend;
  topArticles: TopArticle[];
  topQuestions: TopQuestion[];
  recentQuestions: RecentQuestion[];
}

export const statsApi = {
  overview() {
    return unwrap<StatsOverview>(request.get('/admin/stats/overview'));
  },
  recentQuestions(limit = 10) {
    return unwrap<Paginated<RecentQuestion>>(
      request.get(`/admin/stats/recent-questions?limit=${limit}`),
    );
  },
};

// ===== Knowledge（知识库管理）=====

/**
 * 知识库文档状态机（与后端 pipeline.py 对齐）：
 * - pending:  新建，分块进行中
 * - indexed:  解析→分块→写 PG→embedding→写 Milvus 全部成功
 * - partial:  PG chunks 成功但 Milvus 失败（PG 有 chunks 缺向量）
 * - failed:   解析 / 分块失败
 */
export interface KnowledgeDoc {
  id: string;
  source_type: 'article' | 'upload' | 'policy';
  source_id: string | null;
  title: string;
  raw_uri: string | null;
  // 上传源文件元数据（article 类型为 null）
  original_filename: string | null;
  source_format: 'md' | 'txt' | 'pdf' | 'docx' | null;
  mime_type: string | null;
  source_size: number | null;
  chunk_count: number;
  channel_id: string | null;
  channel_slug: string | null;
  channel_name: string | null;
  status: 'pending' | 'indexed' | 'partial' | 'failed';
  error_msg: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface KnowledgeListParams {
  source_type?: string;
  status?: string;
  channel_id?: string;
  q?: string;
  page?: number;
  size?: number;
}

export interface UploadFailedItem {
  filename: string;
  reason: string;
}

export interface UploadResult {
  created: KnowledgeDoc[];
  failed: UploadFailedItem[];
}

export interface DeleteResult {
  id: string;
  deleted: boolean;
}

export interface ReindexResult {
  doc_id: string;
  task_id: string;
  status: 'queued';
}

export interface RebuildResult {
  task_id: string;
  status: 'queued';
}

export const knowledgeApi = {
  list(params: KnowledgeListParams = {}) {
    const qs = new URLSearchParams();
    if (params.source_type) qs.set('source_type', params.source_type);
    if (params.status) qs.set('status', params.status);
    if (params.channel_id) qs.set('channel_id', params.channel_id);
    if (params.q) qs.set('q', params.q);
    if (params.page) qs.set('page', String(params.page));
    if (params.size) qs.set('size', String(params.size));
    return unwrap<Paginated<KnowledgeDoc>>(
      request.get(`/admin/knowledge/docs${qs.toString() ? `?${qs}` : ''}`),
    );
  },
  /**
   * 多文件多格式上传（md/txt/pdf/docx）。
   * 单文件时 title 生效；多文件时 title 忽略，逐文件从内容/文件名提取。
   * 上传 + 入库（解析/分块/embedding/Milvus）同步执行，timeout 120s。
   */
  upload(files: File[], channelId: string, title?: string) {
    const form = new FormData();
    for (const f of files) {
      form.append('files', f);
    }
    form.append('channel_id', channelId);
    if (title && files.length === 1) form.append('title', title);
    return unwrap<UploadResult>(
      request.post('/admin/knowledge/upload', form, {
        timeout: 120000,
      }),
    );
  },
  /**
   * 下载知识库源文件（从 MinIO 流式返回）。
   * 用原生 fetch 绕过 axios envelope 拦截器，直接拿 Blob + Content-Disposition。
   * 返回 { blob, filename } 供前端触发浏览器下载。
   */
  async download(docId: string): Promise<{ blob: Blob; filename: string }> {
    const base = process.env.NEXT_PUBLIC_API_BASE || '/api';
    const url = `${base}/admin/knowledge/docs/${docId}/download`;
    const resp = await fetch(url, { credentials: 'include' });
    if (!resp.ok) {
      throw new Error(`下载失败: HTTP ${resp.status}`);
    }
    const cd = resp.headers.get('content-disposition') || '';
    const m = /filename="([^"]+)"/.exec(cd);
    const filename = m ? m[1] : docId;
    const blob = await resp.blob();
    return { blob, filename };
  },
  remove(docId: string) {
    return unwrap<DeleteResult>(
      request.delete(`/admin/knowledge/docs/${docId}`),
    );
  },
  reindex(docId: string) {
    return unwrap<ReindexResult>(
      request.post(`/admin/knowledge/docs/${docId}/reindex`),
    );
  },
  rebuild() {
    return unwrap<RebuildResult>(request.post('/admin/knowledge/rebuild'));
  },
};
