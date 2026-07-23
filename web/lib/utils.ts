import { clsx, type ClassValue } from 'clsx';

/** 合并 className（Tailwind 友好） */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/** 日期格式化为 YY-MM-DD（等宽字体友好） */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

/** 防抖 */
export function debounce<T extends (...args: any[]) => void>(fn: T, delay = 300) {
  let timer: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/** slugify:与后端 app/utils/slug.py 逻辑一致(保留中文) */
export function slugify(text: string): string {
  if (!text) return '';
  let s = text.toLowerCase();
  // 非 [a-z0-9中文] 替换为连字符
  s = s.replace(/[^a-z0-9\u4e00-\u9fff]+/g, '-');
  // 去除首尾连字符
  s = s.replace(/^-+|-+$/g, '');
  // 截断到 120 字符
  if (s.length > 120) s = s.slice(0, 120).replace(/-+$/, '');
  return s;
}
