import axios, { type AxiosInstance } from 'axios';

const baseURL = process.env.NEXT_PUBLIC_API_BASE || '/api';

/** 后端统一 envelope 响应格式 */
export interface Envelope<T = unknown> {
  code: number;
  data: T;
  message: string;
}

/**
 * Axios 实例（客户端组件用）。
 * 服务端组件优先用 fetch + Next 缓存。
 *
 * withCredentials=true：跨端口（3000→8000）请求自动携带 cookie，
 * 后台登录依赖 admin_token cookie 鉴权。
 */
export const request: AxiosInstance = axios.create({
  baseURL,
  timeout: 15000,
  withCredentials: true,
});

request.interceptors.request.use((config) => {
  // httpOnly cookie 由浏览器自动携带，此处仅补充匿名会话 ID 用于公开问答
  if (typeof window !== 'undefined') {
    const sessionId = localStorage.getItem('anon_session_id');
    if (sessionId) {
      config.headers['X-Session-Id'] = sessionId;
    }
  }
  return config;
});

request.interceptors.response.use(
  (res) => {
    // unwrap envelope：{code, data, message} → data
    const env = res.data as Envelope;
    if (env && typeof env === 'object' && 'code' in env) {
      if (env.code === 0) return env.data as unknown as never;
      // envelope 层业务错误（含 4010 等）
      // /auth/me 的 4010 不立即跳转，交给 React Query 重试，避免瞬时抖动踢人
      if (env.code === 4010 && !isAuthMeRequest(res?.config)) {
        redirectToLogin();
      }
      return Promise.reject(new Error(env.message || '业务错误'));
    }
    return res.data as unknown as never;
  },
  (error) => {
    const status = error?.response?.status;
    // HTTP 401：cookie 失效或未登录，跳登录页（避免在 /login 自身死循环）
    // 但 /auth/me 的 401 不立即跳转：交给 React Query retry 一次，
    // 重试仍失败再由 useMe 的 onError 触发跳转，避免偶发 401 误伤。
    if (
      status === 401 &&
      typeof window !== 'undefined' &&
      !isAuthMeRequest(error?.config)
    ) {
      redirectToLogin();
    }
    const msg = error?.response?.data?.message || error.message || '请求失败';
    return Promise.reject(new Error(msg));
  },
);

/** 判断请求是否打到 /auth/me（用于 401 容错，不立即跳转） */
function isAuthMeRequest(config: unknown): boolean {
  const url = (config as { url?: string } | undefined)?.url || '';
  return url.includes('/auth/me');
}

function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  const { pathname, search } = window.location;
  if (pathname.startsWith('/login')) return;
  const redirect = encodeURIComponent(pathname + search);
  window.location.href = `/login?redirect=${redirect}`;
}

/**
 * 服务端组件 fetch 封装（RSC 用）。
 * 自动 unwrap envelope，支持 Next.js fetch 的 cache/revalidate 选项。
 *
 * URL 解析优先级：
 *  1. path 是绝对 URL 时直接用
 *  2. API_INTERNAL_URL（server-only env，不暴露浏览器）：prod 部署时设为 http://backend:8000/api
 *  3. NEXT_PUBLIC_API_BASE 如果是绝对 URL（dev 时为 http://localhost:8000/api）
 *  4. fallback: http://localhost:8000/api
 */
function getServerBase(): string {
  const internal = process.env.API_INTERNAL_URL;
  if (internal) return internal;
  const pub = process.env.NEXT_PUBLIC_API_BASE;
  if (pub && /^https?:\/\//.test(pub)) return pub;
  return 'http://localhost:8000/api';
}

export async function serverFetch<T>(
  path: string,
  init?: RequestInit & {
    revalidate?: number;
    tags?: string[];
  },
): Promise<T> {
  const base = getServerBase();
  // 如果是绝对 URL 直接用，否则拼接 base + path
  const url = path.startsWith('http')
    ? path
    : `${base}${path.startsWith('/') ? path : `/${path}`}`;

  const { revalidate, tags, ...restInit } = init ?? {};
  // next 选项：tags 优先（可被 revalidateTag 精准失效），其次 revalidate（时间缓存）
  const next: Record<string, unknown> = {};
  if (tags?.length) next.tags = tags;
  if (revalidate !== undefined) next.revalidate = revalidate;

  const res = await fetch(url, {
    ...restInit,
    next: Object.keys(next).length ? next : undefined,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${url}`);
  }
  const env = (await res.json()) as Envelope<T>;
  if (env.code !== 0) {
    throw new Error(env.message || '业务错误');
  }
  return env.data;
}
