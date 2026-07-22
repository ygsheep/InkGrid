'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import RoleCard from '@/components/chat/RoleCard';
import { usePersona } from '@/lib/usePersona';

/**
 * 角色选择页 — 参考 plan/角色选择.html。
 * 卡片网格 + 扫描线 hover + 序号 + 标签芯片 + 初始化身份按钮。
 */
export default function PersonaPage() {
  const { personaId, personas, select, hydrated } = usePersona();
  const router = useRouter();

  const handleBack = () => {
    if (window.history.length > 1) router.back();
    else router.push('/ask');
  };

  return (
    <div className="flex-1 spatial-grid overflow-y-auto">
      <div className="relative z-10 mx-auto max-w-page-7xl px-margin-mobile md:px-margin-desktop py-12 md:py-20">
        {/* Hero */}
        <div className="mb-16 md:mb-20">
          <button
            onClick={handleBack}
            className="font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest flex items-center gap-2 mb-6"
          >
            <ArrowLeft size={14} />
            返回
          </button>
          <div className="flex items-center gap-4 mb-4">
            <div className="h-px w-12 bg-primary" />
            <span className="font-mono text-label-mono tracking-widest text-primary uppercase">
              身份选择协议
            </span>
          </div>
          <h1 className="font-headline text-headline-lg-mobile md:text-headline-lg text-primary leading-tight tracking-tighter mb-6">
            选择你的实体
          </h1>
          <p className="font-sans text-body-md text-on-surface-variant max-w-xl">
            定义对话参数及对话伙伴的语义结构。每个角色代表一个独特的认知框架与回答风格。
          </p>
        </div>

        {/* 卡片网格 — 1px 共享边框 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0 border-l border-t border-outline-variant">
          {personas.map((p) => (
            <RoleCard
              key={p.id}
              persona={p}
              selected={hydrated && p.id === personaId}
              onSelect={select}
            />
          ))}
        </div>

        {/* 底部元信息 */}
        <footer className="mt-20 md:mt-32 pt-8 md:pt-12 border-t border-outline-variant flex flex-col md:flex-row justify-between items-start gap-6">
          <div className="max-w-md">
            <span className="font-mono text-label-mono text-outline-variant uppercase tracking-widest mb-3 block">
              系统状态
            </span>
            <p className="font-mono text-label-mono text-on-surface-variant uppercase tracking-wider">
              所有实体已与知识库核心同步。延迟 &lt; 14ms。
            </p>
          </div>
          <div className="flex flex-col gap-2 md:text-right">
            <span className="font-mono text-label-mono text-outline-variant uppercase tracking-widest">
              当前会话
            </span>
            <span className="font-mono text-label-mono text-primary uppercase tracking-widest">
              {hydrated
                ? `实体_${personas.find((p) => p.id === personaId)?.serial ?? '000'}`
                : '实体_001'}
            </span>
            <span className="font-mono text-label-mono text-primary uppercase tracking-widest">
              全程端到端加密
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}
