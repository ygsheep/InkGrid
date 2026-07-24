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
  knowledgeApi,
  personasApi,
  postsApi,
  settingsApi,
  statsApi,
  type AdminChannel,
  type AdminInfo,
  type AdminPersona,
  type AdminPost,
  type ChannelCreatePayload,
  type ChannelUpdatePayload,
  type DeleteResult,
  type KnowledgeDoc,
  type KnowledgeListParams,
  type PersonaCreatePayload,
  type PersonaUpdatePayload,
  type PostCreatePayload,
  type PostListParams,
  type PostUpdatePayload,
  type PostUploadResult,
  type RecentQuestion,
  type RebuildResult,
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
  knowledgeDocs: (params: KnowledgeListParams) =>
    ['admin', 'knowledge', 'docs', params] as const,
  settings: ['admin', 'settings'] as const,
  statsOverview: ['admin', 'stats', 'overview'] as const,
  statsRecentQuestions: (limit: number) =>
    ['admin', 'stats', 'recent-questions', limit] as const,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (vars) => authApi.login(vars),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: adminKeys.me });
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useLogout(
  opts?: UseMutationOptions<{ ok: boolean }, Error, void>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: () => authApi.logout(),
    onSuccess: (...args) => {
      qc.clear();
      onSuccess?.(...args);
    },
    onError,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (payload) => postsApi.create(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      onSuccess?.(...args);
    },
    onError,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: ({ id, payload }) => postsApi.update(id, payload),
    onSuccess: (data, vars, ...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      qc.setQueryData(adminKeys.post(vars.id), data);
      onSuccess?.(data, vars, ...args);
    },
    onError,
  });
}

export function useDeletePost(
  opts?: UseMutationOptions<{ ok: boolean }, Error, string>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (id) => postsApi.remove(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useSetPostStatus(
  opts?: UseMutationOptions<AdminPost, Error, { id: string; status: string }>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: ({ id, status }) => postsApi.setStatus(id, status),
    onSuccess: (data, vars, ...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      qc.setQueryData(adminKeys.post(vars.id), data);
      onSuccess?.(data, vars, ...args);
    },
    onError,
  });
}

export function useUploadPostMd(
  opts?: UseMutationOptions<
    PostUploadResult,
    Error,
    { files: File[]; channelId: string }
  >,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: ({ files, channelId }) => postsApi.uploadMd(files, channelId),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'posts'] });
      onSuccess?.(...args);
    },
    onError,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (payload) => channelsApi.create(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'channels'] });
      onSuccess?.(...args);
    },
    onError,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: ({ id, payload }) => channelsApi.update(id, payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'channels'] });
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useDeleteChannel(
  opts?: UseMutationOptions<{ ok: boolean }, Error, string>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (id) => channelsApi.remove(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'channels'] });
      onSuccess?.(...args);
    },
    onError,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (payload) => personasApi.create(payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'personas'] });
      onSuccess?.(...args);
    },
    onError,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: ({ id, payload }) => personasApi.update(id, payload),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'personas'] });
      onSuccess?.(...args);
    },
    onError,
  });
}

export function useDeletePersona(
  opts?: UseMutationOptions<{ ok: boolean }, Error, string>,
) {
  const qc = useQueryClient();
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (id: string) => personasApi.remove(id),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ['admin', 'personas'] });
      onSuccess?.(...args);
    },
    onError,
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
  const { onSuccess, onError, ...rest } = opts ?? {};
  return useMutation({
    ...rest,
    mutationFn: (payload) => settingsApi.update(payload),
    onSuccess: (data, vars, ...args) => {
      qc.setQueryData(adminKeys.settings, data);
      onSuccess?.(data, vars, ...args);
    },
    onError,
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

// ===== Knowledge（知识库管理）=====

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
      // 下载不需要刷新列表
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
      // 异步任务派发后，列表状态不会立即变化；延迟 3s 刷新一次
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
      // 全量重建耗时较长，延迟 5s 刷新一次列表
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['admin', 'knowledge', 'docs'] });
      }, 5000);
      onSuccess?.(...args);
    },
    onError,
  });
}
