'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';

interface AskBoxProps {
  /** 限定问答范围（频道 slug），不传为全站 */
  scope?: string;
  placeholder?: string;
}

/**
 * AskBox — 1px outline-variant border that promotes to primary on focus.
 * Primary action: solid white fill, black text, zero radius.
 */
export default function AskBox({ scope, placeholder }: AskBoxProps) {
  const [q, setQ] = useState('');
  const router = useRouter();

  const submit = () => {
    if (!q.trim()) return;
    const params = new URLSearchParams({ q: q.trim() });
    if (scope) params.set('scope', scope);
    router.push(`/ask?${params.toString()}`);
  };

  return (
    <div className="flex w-full border border-outline-variant focus-within:border-primary transition-colors">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') submit();
        }}
        placeholder={placeholder || '向 AI 提问…它基于我的文章回答'}
        className="flex-1 bg-transparent px-4 py-3 font-mono text-body-sm text-on-surface placeholder:text-outline focus:outline-none"
      />
      <button
        onClick={submit}
        className="bg-primary text-on-primary px-6 py-3 font-mono text-label-mono uppercase tracking-widest flex items-center gap-2 hover:bg-primary/90 transition-colors"
      >
        提问
        <ArrowRight size={14} />
      </button>
    </div>
  );
}
