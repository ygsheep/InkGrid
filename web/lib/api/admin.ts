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
  uploadMd(file: File, channelId: string) {
    const form = new FormData();
    form.append('file', file);
    form.append('channel_id', channelId);
    // axios 检测到 FormData 会自动设置 multipart/form-data boundary
    return unwrap<AdminPost>(
      request.post('/admin/posts/upload', form, {
        timeout: 30000, // 文件上传放宽超时
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

// ===== Q&A 审核 =====

export interface AdminQaPair {
  id: string;
  article_id: string;
  question: string;
  answer: string;
  status: 'pending' | 'approved' | 'rejected';
  milvus_chunk_id: string | null;
  created_at: string;
  updated_at: string;
  article_title: string | null;
}

export interface QaListParams {
  status?: string;
  article_id?: string;
  page?: number;
  size?: number;
}

export interface QaReviewPayload {
  status: 'approved' | 'rejected';
  question?: string;
  answer?: string;
}

export const qaApi = {
  list(params: QaListParams = {}) {
    const qs = new URLSearchParams();
    if (params.status) qs.set('status', params.status);
    if (params.article_id) qs.set('article_id', params.article_id);
    if (params.page) qs.set('page', String(params.page));
    if (params.size) qs.set('size', String(params.size));
    return unwrap<Paginated<AdminQaPair>>(
      request.get(`/admin/qa${qs.toString() ? `?${qs}` : ''}`),
    );
  },
  get(id: string) {
    return unwrap<AdminQaPair>(request.get(`/admin/qa/${id}`));
  },
  review(id: string, payload: QaReviewPayload) {
    return unwrap<AdminQaPair>(request.patch(`/admin/qa/${id}`, payload));
  },
  reindex(id: string) {
    return unwrap<{ qa_id: string; milvus_chunk_id: string }>(
      request.post(`/admin/qa/${id}/reindex`),
    );
  },
};

// ===== Knowledge Base（知识库）=====

/** 笔记 7 层 category 枚举 */
export type KbCategory =
  | 'inbox'
  | 'daily'
  | 'reading'
  | 'knowledge'
  | 'projects'
  | 'templates'
  | 'assets';

/** 目录树顶层节点 */
export interface KbTreeNode {
  key: string; // category，如 "knowledge"
  label: string; // 显示名，如 "主题知识"
  code: string; // 目录前缀，如 "03_Knowledge"
  count: number;
  children: KbTreeFolder[];
}

/** 目录树子文件夹节点 */
export interface KbTreeFolder {
  key: string; // 完整 folder_path，如 "knowledge/大模型"
  label: string; // 显示名，如 "大模型"
  count: number;
}

/** 笔记列表项（轻量，不含正文） */
export interface KbNoteListItem {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  category: string;
  folder_path: string | null;
  is_moc: boolean;
  tags: string[];
  status: 'draft' | 'private' | 'published';
  published_at: string | null;
  updated_at: string | null;
}

/** 笔记详情 */
export interface KbNote extends KbNoteListItem {
  content_md: string;
  source_url: string | null;
  owner_id: string | null;
  channel_id: string | null;
  channel_slug: string | null;
  channel_name: string | null;
  reading_time: number | null;
  created_at: string | null;
  outlinks?: KbNoteLink[]; // 详情接口才返回
}

/** 双链关系 */
export interface KbNoteLink {
  id: string;
  target_note_id: string | null;
  target_title_raw: string;
  source_note_id?: string | null;
  source_title?: string | null;
}

/** 笔记模板 */
export interface KbTemplate {
  id: string;
  name: string;
  category: string;
  description: string | null;
  content_md: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface KbNoteListParams {
  category?: string;
  folder_path?: string; // "null" 字符串表示该 category 下无子目录
  tag?: string;
  q?: string;
  page?: number;
  size?: number;
}

export interface KbNoteCreatePayload {
  slug?: string;
  title: string;
  excerpt?: string | null;
  content_md: string;
  channel_id?: string | null;
  category?: string;
  folder_path?: string | null;
  is_moc?: boolean;
  source_url?: string | null;
  tags?: string[] | null;
  status?: string;
  reading_time?: number | null;
  toc?: unknown[] | null;
}

export type KbNoteUpdatePayload = Partial<KbNoteCreatePayload>;

export interface KbTemplateCreatePayload {
  name: string;
  category: string;
  description?: string | null;
  content_md: string;
}

export const kbApi = {
  // 目录树
  tree() {
    return unwrap<KbTreeNode[]>(request.get('/admin/kb/tree'));
  },

  // 笔记列表
  listNotes(params: KbNoteListParams = {}) {
    const qs = new URLSearchParams();
    if (params.category) qs.set('category', params.category);
    if (params.folder_path !== undefined)
      qs.set('folder_path', params.folder_path);
    if (params.tag) qs.set('tag', params.tag);
    if (params.q) qs.set('q', params.q);
    if (params.page) qs.set('page', String(params.page));
    if (params.size) qs.set('size', String(params.size));
    return unwrap<Paginated<KbNoteListItem>>(
      request.get(`/admin/kb/notes${qs.toString() ? `?${qs}` : ''}`),
    );
  },

  // 笔记详情
  getNote(id: string) {
    return unwrap<KbNote>(request.get(`/admin/kb/notes/${id}`));
  },

  // 新建笔记
  createNote(payload: KbNoteCreatePayload) {
    return unwrap<KbNote>(request.post('/admin/kb/notes', payload));
  },

  // 更新笔记
  updateNote(id: string, payload: KbNoteUpdatePayload) {
    return unwrap<KbNote>(request.patch(`/admin/kb/notes/${id}`, payload));
  },

  // 删除笔记
  deleteNote(id: string) {
    return unwrap<{ ok: boolean }>(request.delete(`/admin/kb/notes/${id}`));
  },

  // 反链面板
  backlinks(id: string) {
    return unwrap<KbNoteLink[]>(
      request.get(`/admin/kb/notes/${id}/backlinks`),
    );
  },

  // 模板列表
  listTemplates(category?: string) {
    const qs = new URLSearchParams();
    if (category) qs.set('category', category);
    return unwrap<KbTemplate[]>(
      request.get(`/admin/kb/templates${qs.toString() ? `?${qs}` : ''}`),
    );
  },

  // 新建模板
  createTemplate(payload: KbTemplateCreatePayload) {
    return unwrap<KbTemplate>(request.post('/admin/kb/templates', payload));
  },
};
