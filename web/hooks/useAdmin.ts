/**
 * 后台 admin 模块 React Query hooks。
 *
 * Query Key 约定：
 *  - ['admin', 'posts', params]
 *  - ['admin', 'post', id]
 *  - ['admin', 'channels', params]
 *  - ['admin', 'personas', params]
 *  - ['admin', 'settings']
 *  - ['admin', 'me']
 *
 * Mutation 后通过 queryClient.invalidateQueries 自动刷新对应列表。
 */
'use client';

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
} from '@tanstack/react-query';
import {
  authApi,
  channelsApi,
  kbApi,
  knowledgeApi,
  personasApi,
  postsApi,
  qaApi,
  settingsApi,
  statsApi,
  type AdminChannel,
  type AdminInfo,
  type AdminPersona,
  type AdminPost,
  type AdminQaPair,
  type ChannelCreatePayload,
  type ChannelUpdatePayload,
  type DeleteResult,
  type KbNote,
  type KbNoteCreatePayload,
  type KbNoteLink,
  type KbNoteListParams,
  type KbNoteListItem,
  type KbNoteUpdatePayload,
  type KbTemplate,
  type KbTemplateCreatePayload,
  type KbTreeNode,
  type KnowledgeDoc,
  type KnowledgeListParams,
  type PersonaCreatePayload,
  type PersonaUpdatePayload,
  type PostCreatePayload,
  type PostListParams,
  type PostUpdatePayload,
  type QaListParams,
  type QaReviewPayload,
  type RebuildResult,
  type RecentQuestion,
  type ReindexResult,
  type SettingsUpdatePayload,
  type SiteSettings,
  type StatsOverview,
  type UploadResult,
} from '@/lib/api/admin';
import type { Paginated } from '@/lib/api';

// ===== Query Keys =====

export const adminKeys = {
  me: ['admin', 'me'] as const,
  posts: (params: PostListParams) => ['admin', 'posts', params] as const,
  post: (id: string) => ['admin', 'post', id] as const,
  channels: (params: { page?: number; size?: number }) =>
    ['admin', 'channels', params] as const,
  personas: (params: { scope?: string; page?: number; size?: number }) =>
    ['admin', 'personas', params] as const,
  persona: (id: string) => ['admin', 'persona', id] as const,
  qa: (params: QaListParams) => ['admin', 'qa', params] as const,
  qaDetail: (id: string) => ['admin', 'qa', 'detail', id] as const,
  knowledgeDocs: (params: KnowledgeListParams) =>
    ['admin', 'knowledge', 'docs', params] as const,
  settings: ['admin', 'settings'] as const,
  statsOverview: ['admin', 'stats', 'overview'] as const,
  statsRecentQuestions: (limit: number) =>
    ['admin', 'stats', 'recent-questions', limit] as const,
  // Knowledge Base
  kbTree: ['admin', 'kb', 'tree'] as const,
  kbNotes: (params: KbNoteListParams) => ['admin', 'kb', 'notes', params] as const,
  kbNote: (id: string) => ['admin', 'kb', 'note', id] as const,
  kbBacklinks: (id: string) => ['admin', 'kb', 'backlinks', id] as const,
  kbTemplates: (category?: string) =>
    ['admin', 'kb', 'templates', category] as const,
};

// ===== Auth =====

export function useMe(opts?: UseQueryOptions<AdminInfo>) {
  return useQuery({
    queryKey: adminKeys.me,
    queryFn: () => authApi.me(),
    // me 是隐式校验：失败（401）会被 request 拦截器跳转 /login
    retry: 0,
    staleTime: 60_000,
    ...opts,
  });
}

export function useLogin(
  opts?: UseMutationOptions<
    AdminInfo,
    Error,
    { username: string; password: string }
  >,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars) => authApi.login(vars),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: adminKeys.me });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

export function useLogout(
  opts?: UseMutationOptions<{ ok: boolean }, Error, void>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: (...args) => {
      // 清空所有 admin 缓存
      qc.clear();
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

// ===== Posts =====

export function useAdminPosts(
  params: PostListParams = {},
  opts?: UseQueryOptions<Paginated<AdminPost>>,
) {
  return useQuery({
    queryKey: adminKeys.posts(params),
    queryFn: () => postsApi.list(params),
    ...opts,
  });
}

export function useAdminPost(
  id: string,
  opts?: UseQueryOptions<AdminPost>,
) {
  return useQuery({
    queryKey: adminKeys.post(id),
    queryFn: () => postsApi.get(id),
    enabled: !!id,
    ...opts,
  });
}

export function useCreatePost(
  opts?: UseMutationOptions<AdminPost, Error, PostCreatePayload>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => postsApi.create(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

export function useUpdatePost(
  opts?: UseMutationOptions<
    AdminPost,
    Error,
    { id: string; payload: PostUpdatePayload }
  >,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }) => postsApi.update(id, payload),
    onSuccess: (data, vars, ...rest) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      qc.setQueryData(adminKeys.post(vars.id), data);
      opts?.onSuccess?.(data, vars, ...rest);
    },
    ...opts,
  });
}

export function useDeletePost(
  opts?: UseMutationOptions<{ ok: boolean }, Error, string>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => postsApi.remove(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

export function useSetPostStatus(
  opts?: UseMutationOptions<AdminPost, Error, { id: string; status: string }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }) => postsApi.setStatus(id, status),
    onSuccess: (data, vars, ...rest) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      qc.setQueryData(adminKeys.post(vars.id), data);
      opts?.onSuccess?.(data, vars, ...rest);
    },
    ...opts,
  });
}

export function useUploadPostMd(
  opts?: UseMutationOptions<AdminPost, Error, { file: File; channelId: string }>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, channelId }) => postsApi.uploadMd(file, channelId),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

// ===== Channels =====

export function useAdminChannels(
  params: { page?: number; size?: number } = {},
  opts?: UseQueryOptions<Paginated<AdminChannel>>,
) {
  return useQuery({
    queryKey: adminKeys.channels(params),
    queryFn: () => channelsApi.list(params),
    ...opts,
  });
}

export function useCreateChannel(
  opts?: UseMutationOptions<AdminChannel, Error, ChannelCreatePayload>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => channelsApi.create(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'channels'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

export function useUpdateChannel(
  opts?: UseMutationOptions<
    AdminChannel,
    Error,
    { id: string; payload: ChannelUpdatePayload }
  >,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }) => channelsApi.update(id, payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'channels'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

export function useDeleteChannel(
  opts?: UseMutationOptions<{ ok: boolean }, Error, string>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => channelsApi.remove(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'channels'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

// ===== Personas =====

export function useAdminPersonas(
  params: { scope?: string; page?: number; size?: number } = {},
  opts?: UseQueryOptions<Paginated<AdminPersona>>,
) {
  return useQuery({
    queryKey: adminKeys.personas(params),
    queryFn: () => personasApi.list(params),
    ...opts,
  });
}

export function useCreatePersona(
  opts?: UseMutationOptions<AdminPersona, Error, PersonaCreatePayload>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => personasApi.create(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'personas'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

export function useUpdatePersona(
  opts?: UseMutationOptions<
    AdminPersona,
    Error,
    { id: string; payload: PersonaUpdatePayload }
  >,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }) => personasApi.update(id, payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'personas'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

export function useDeletePersona(
  opts?: UseMutationOptions<{ ok: boolean }, Error, string>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => personasApi.remove(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'personas'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

// ===== Settings =====

export function useAdminSettings(opts?: UseQueryOptions<SiteSettings>) {
  return useQuery({
    queryKey: adminKeys.settings,
    queryFn: () => settingsApi.get(),
    ...opts,
  });
}

export function useUpdateSettings(
  opts?: UseMutationOptions<SiteSettings, Error, SettingsUpdatePayload>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => settingsApi.update(payload),
    onSuccess: (data, vars, ...rest) => {
      qc.setQueryData(adminKeys.settings, data);
      opts?.onSuccess?.(data, vars, ...rest);
    },
    ...opts,
  });
}

// ===== Stats（数据看板）=====

export function useStatsOverview(opts?: UseQueryOptions<StatsOverview>) {
  return useQuery({
    queryKey: adminKeys.statsOverview,
    queryFn: () => statsApi.overview(),
    // 看板数据相对稳定，30s 内不重复请求
    staleTime: 30_000,
    ...opts,
  });
}

export function useStatsRecentQuestions(
  limit = 10,
  opts?: UseQueryOptions<Paginated<RecentQuestion>>,
) {
  return useQuery({
    queryKey: adminKeys.statsRecentQuestions(limit),
    queryFn: () => statsApi.recentQuestions(limit),
    staleTime: 30_000,
    ...opts,
  });
}

// ===== Q&A 审核 =====

export function useAdminQa(
  params: QaListParams = {},
  opts?: UseQueryOptions<Paginated<AdminQaPair>>,
) {
  return useQuery({
    queryKey: adminKeys.qa(params),
    queryFn: () => qaApi.list(params),
    ...opts,
  });
}

export function useAdminQaDetail(
  id: string,
  opts?: UseQueryOptions<AdminQaPair>,
) {
  return useQuery({
    queryKey: adminKeys.qaDetail(id),
    queryFn: () => qaApi.get(id),
    enabled: !!id,
    ...opts,
  });
}

export function useReviewQa(
  opts?: UseMutationOptions<
    AdminQaPair,
    Error,
    { id: string; payload: QaReviewPayload }
  >,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }) => qaApi.review(id, payload),
    onSuccess: (data, vars, ...rest) => {
      qc.invalidateQueries({ queryKey: ['admin', 'qa'] });
      qc.setQueryData(adminKeys.qaDetail(vars.id), data);
      opts?.onSuccess?.(data, vars, ...rest);
    },
    ...opts,
  });
}

export function useReindexQa(
  opts?: UseMutationOptions<{ qa_id: string; milvus_chunk_id: string }, Error, string>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => qaApi.reindex(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'qa'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

// ===== Knowledge Base =====

/** 目录树 */
export function useKbTree(opts?: UseQueryOptions<KbTreeNode[]>) {
  return useQuery({
    queryKey: adminKeys.kbTree,
    queryFn: () => kbApi.tree(),
    ...opts,
  });
}

/** 笔记列表 */
export function useKbNotes(
  params: KbNoteListParams = {},
  opts?: UseQueryOptions<Paginated<KbNoteListItem>>,
) {
  return useQuery({
    queryKey: adminKeys.kbNotes(params),
    queryFn: () => kbApi.listNotes(params),
    ...opts,
  });
}

/** 笔记详情 */
export function useKbNote(
  id: string,
  opts?: UseQueryOptions<KbNote>,
) {
  return useQuery({
    queryKey: adminKeys.kbNote(id),
    queryFn: () => kbApi.getNote(id),
    enabled: !!id,
    ...opts,
  });
}

/** 反链面板 */
export function useKbBacklinks(
  id: string,
  opts?: UseQueryOptions<KbNoteLink[]>,
) {
  return useQuery({
    queryKey: adminKeys.kbBacklinks(id),
    queryFn: () => kbApi.backlinks(id),
    enabled: !!id,
    ...opts,
  });
}

/** 模板列表 */
export function useKbTemplates(
  category?: string,
  opts?: UseQueryOptions<KbTemplate[]>,
) {
  return useQuery({
    queryKey: adminKeys.kbTemplates(category),
    queryFn: () => kbApi.listTemplates(category),
    ...opts,
  });
}

/** 新建笔记 */
export function useCreateKbNote(
  opts?: UseMutationOptions<KbNote, Error, KbNoteCreatePayload>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => kbApi.createNote(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'kb'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

/** 更新笔记 */
export function useUpdateKbNote(
  opts?: UseMutationOptions<
    KbNote,
    Error,
    { id: string; payload: KbNoteUpdatePayload }
  >,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }) => kbApi.updateNote(id, payload),
    onSuccess: (data, vars, ...rest) => {
      qc.setQueryData(adminKeys.kbNote(vars.id), data);
      qc.invalidateQueries({ queryKey: ['admin', 'kb', 'notes'] });
      qc.invalidateQueries({ queryKey: ['admin', 'kb', 'tree'] });
      opts?.onSuccess?.(data, vars, ...rest);
    },
    ...opts,
  });
}

/** 删除笔记 */
export function useDeleteKbNote(
  opts?: UseMutationOptions<{ ok: boolean }, Error, string>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => kbApi.deleteNote(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'kb'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

/** 新建模板 */
export function useCreateKbTemplate(
  opts?: UseMutationOptions<KbTemplate, Error, KbTemplateCreatePayload>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => kbApi.createTemplate(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'kb', 'templates'] });
      opts?.onSuccess?.(...args);
    },
    ...opts,
  });
}

// ===== Knowledge Docs（知识库文档管理）=====

export function useKnowledgeDocs(
  params: KnowledgeListParams = {},
  opts?: UseQueryOptions<Paginated<KnowledgeDoc>>,
) {
  return useQuery({
    queryKey: adminKeys.knowledgeDocs(params),
    queryFn: () => knowledgeApi.list(params),
    ...opts,
  });
}

export function useUploadKnowledgeDoc(
  opts?: UseMutationOptions<
    UploadResult,
    Error,
    { files: File[]; channelId: string; title?: string }
  >,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: ({ files, channelId, title }) =>
      knowledgeApi.upload(files, channelId, title),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'knowledge', 'docs'] });
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useDeleteKnowledgeDoc(
  opts?: UseMutationOptions<DeleteResult, Error, string>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (docId: string) => knowledgeApi.remove(docId),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'knowledge', 'docs'] });
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useDownloadKnowledgeDoc(
  opts?: UseMutationOptions<
    { blob: Blob; filename: string },
    Error,
    string
  >,
) {
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (docId: string) => knowledgeApi.download(docId),
    onSuccess: (...args) => {
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useReindexKnowledgeDoc(
  opts?: UseMutationOptions<ReindexResult, Error, string>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (docId: string) => knowledgeApi.reindex(docId),
    onSuccess: (...args) => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['admin', 'knowledge', 'docs'] });
      }, 3000);
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useRebuildKnowledge(
  opts?: UseMutationOptions<RebuildResult, Error, void>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: () => knowledgeApi.rebuild(),
    onSuccess: (...args) => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['admin', 'knowledge', 'docs'] });
      }, 5000);
      onSuccess?.(...args);
    },
    onError,
  });
}
