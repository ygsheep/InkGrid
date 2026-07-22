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
