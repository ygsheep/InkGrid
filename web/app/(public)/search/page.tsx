'use client';

import { useState } from 'react';
import { Search as SearchIcon } from 'lucide-react';

export default function SearchPage() {
  const [q, setQ] = useState('');

  return (
    <div className="border-b border-outline-variant">
      <section className="mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-grid-major">
        <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter mb-2">
          搜索
        </h1>
        <p className="font-mono text-label-mono text-on-surface-variant mb-12 uppercase">
          SEARCH · 全站文章索引
        </p>

        <div className="flex border border-outline-variant focus-within:border-primary transition-colors">
          <span className="flex items-center pl-4 text-on-surface-variant">
            <SearchIcon size={16} />
          </span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索架构、协议或见解…（接入 Meilisearch 后启用）"
            className="flex-1 bg-transparent px-4 py-3 font-mono text-body-sm text-on-surface placeholder:text-outline focus:outline-none"
          />
        </div>

        {!q && (
          <p className="font-mono text-label-mono text-on-surface-variant mt-12 text-center uppercase tracking-widest">
            输入关键词，即时搜索全站文章
          </p>
        )}
      </section>
    </div>
  );
}
