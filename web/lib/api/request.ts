import axios, { type AxiosInstance } from 'axios';

const baseURL = process.env.NEXT_PUBLIC_API_BASE || '/api';

/**
 * Axios 实例（客户端组件用）。
 * 服务端组件优先用 fetch + Next 缓存。
 */
export const request: AxiosInstance = axios.create({
  baseURL,
  timeout: 15000,
});

request.interceptors.request.use((config) => {
  // 后台接口注入 admin token（httpOnly cookie 由浏览器自动携带，
  // 此处仅补充匿名会话 ID 用于公开问答）
  if (typeof window !== 'undefined') {
    const sessionId = localStorage.getItem('anon_session_id');
    if (sessionId) {
      config.headers['X-Session-Id'] = sessionId;
    }
  }
  return config;
});

request.interceptors.response.use(
  (res) => res.data,
  (error) => {
    const msg = error?.response?.data?.message || error.message || '请求失败';
    return Promise.reject(new Error(msg));
  },
);
