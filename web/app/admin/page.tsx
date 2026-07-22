'use client';

import { FileText, MessageSquare, Database, Eye } from 'lucide-react';

const stats = [
  { title: '文章数', value: 6, icon: FileText, unit: 'POSTS' },
  { title: '问答次数', value: 128, icon: MessageSquare, unit: 'QUERIES' },
  { title: '知识库文档', value: 24, icon: Database, unit: 'DOCS' },
  { title: '本月访问', value: 1532, icon: Eye, unit: 'VIEWS' },
];

export default function AdminHomePage() {
  return (
    <div>
      <h1 className="font-headline text-headline-md text-primary uppercase tracking-tighter">
        数据看板
      </h1>
      <p className="font-mono text-label-mono text-on-surface-variant mt-2 mb-12 uppercase tracking-widest">
        DASHBOARD · 站点运营概览
      </p>

      {/* Stat grid — Data Table aesthetic: mono numerics, 1px borders */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 border border-outline-variant">
        {stats.map((s, i) => (
          <div
            key={s.title}
            className={`p-6 bg-surface-container-lowest flex flex-col gap-3 ${
              i !== stats.length - 1 ? 'border-b sm:border-b-0 sm:border-r border-outline-variant' : ''
            } ${i === 1 ? 'sm:border-b lg:border-b-0' : ''} ${i === 2 ? 'lg:border-b-0 sm:border-r' : ''}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-label-mono text-on-surface-variant uppercase tracking-widest">
                {s.title}
              </span>
              <s.icon size={16} className="text-on-surface-variant" />
            </div>
            <div className="font-mono text-3xl text-primary tabular-nums">
              {s.value}
            </div>
            <span className="font-mono text-label-mono text-tertiary-fixed uppercase tracking-widest">
              {s.unit}
            </span>
          </div>
        ))}
      </div>

      <h2 className="font-headline text-headline-md text-primary uppercase tracking-tighter mt-12 mb-4">
        最近问答
      </h2>
      <div className="border border-outline-variant bg-surface-container-lowest p-8">
        <p className="font-mono text-label-mono text-on-surface-variant py-12 text-center uppercase tracking-widest">
          接入后端后展示最近问答记录
        </p>
      </div>
    </div>
  );
}
