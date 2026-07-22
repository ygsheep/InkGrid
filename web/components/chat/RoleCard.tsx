'use client';

import { Check } from 'lucide-react';
import type { Persona } from '@/types';

interface RoleCardProps {
  persona: Persona;
  selected: boolean;
  onSelect: (id: string) => void;
}

/**
 * RoleCard — 参考角色选择.html，自适应布局：
 *  - 移动端：横向紧凑（左小头像 + 右内容），适合单列浏览
 *  - 桌面端：纵向 4:5 头像在上、内容在下，3 列网格
 *  - 扫描线 hover、序号、标签芯片、"初始化身份"按钮
 *
 * 选中后不自动跳转——用户通过页面顶部"返回"按钮自行决定去留，
 * 避免从导航栏直接进入时被强制跳到对话页。
 */
export default function RoleCard({
  persona,
  selected,
  onSelect,
}: RoleCardProps) {
  return (
    <div
      className={`character-card group relative border-r border-b border-outline-variant bg-surface-container-lowest p-4 sm:p-6 md:p-8 cursor-pointer overflow-hidden transition-colors duration-300 ${
        selected ? 'ring-1 ring-inset ring-tertiary-fixed' : ''
      }`}
    >
      {/* 扫描线 */}
      <div className="scanline opacity-0 group-hover:opacity-100" />

      {/* 移动端：横向布局 */}
      <div className="flex gap-4 md:hidden">
        {/* 小头像 */}
        <div
          className={`w-20 h-24 shrink-0 relative overflow-hidden border flex items-center justify-center ${
            selected
              ? 'border-tertiary-fixed bg-tertiary-fixed/5'
              : 'border-outline-variant group-hover:border-primary'
          }`}
        >
          <div
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
              backgroundSize: '8px 8px',
            }}
          />
          <span className="relative font-headline text-3xl text-primary/80 group-hover:text-primary transition-colors">
            {persona.name.charAt(0)}
          </span>
          {selected && (
            <div className="absolute top-1 right-1 w-5 h-5 bg-tertiary-fixed text-on-tertiary flex items-center justify-center">
              <Check size={12} strokeWidth={3} />
            </div>
          )}
        </div>

        {/* 右内容 */}
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex justify-between items-start gap-2 mb-1">
            <span className="font-mono text-label-mono text-outline-variant uppercase tracking-widest">
              {`${persona.serial} // 代理`}
            </span>
            <div
              className={`w-1.5 h-1.5 ${selected ? 'bg-tertiary-fixed' : 'bg-primary'}`}
            />
          </div>
          <h3 className="font-headline text-xl text-primary tracking-tighter leading-tight">
            {persona.name}
          </h3>
          <span className="font-mono text-label-mono text-tertiary-fixed-dim uppercase tracking-widest mt-0.5">
            {persona.tagline}
          </span>
          <p className="font-sans text-body-sm text-on-surface-variant mt-2 line-clamp-2">
            {persona.description}
          </p>
          <button
            onClick={() => onSelect(persona.id)}
            className={`mt-auto pt-3 font-mono text-label-mono uppercase tracking-widest transition-colors text-left ${
              selected
                ? 'text-tertiary-fixed cursor-default'
                : 'text-primary hover:text-tertiary-fixed-dim'
            }`}
            disabled={selected}
          >
            {selected ? '✓ 当前身份' : '初始化身份 →'}
          </button>
        </div>
      </div>

      {/* 桌面端：纵向布局 */}
      <div className="hidden md:block">
        {/* 序号 + 角标 */}
        <div className="flex justify-between items-start mb-8">
          <span className="font-mono text-label-mono text-outline-variant uppercase tracking-widest">
            {`${persona.serial} // 代理类型`}
          </span>
          <div
            className={`w-2 h-2 ${selected ? 'bg-tertiary-fixed' : 'bg-primary'}`}
          />
        </div>

        {/* 4:5 头像 */}
        <div
          className={`aspect-[4/5] w-full mb-8 relative overflow-hidden border transition-colors duration-500 flex items-center justify-center ${
            selected
              ? 'border-tertiary-fixed bg-tertiary-fixed/5'
              : 'border-outline-variant group-hover:border-primary'
          }`}
        >
          <div
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
              backgroundSize: '8px 8px',
            }}
          />
          <span className="relative font-headline text-6xl text-primary/80 group-hover:text-primary transition-colors">
            {persona.name.charAt(0)}
          </span>
          <div className="absolute inset-0 border-t border-white/10" />
          {selected && (
            <div className="absolute top-2 right-2 w-6 h-6 bg-tertiary-fixed text-on-tertiary flex items-center justify-center">
              <Check size={14} strokeWidth={3} />
            </div>
          )}
        </div>

        {/* 内容 */}
        <div className="relative z-10">
          <div className="flex items-baseline justify-between gap-2 mb-2">
            <h3 className="font-headline text-2xl lg:text-3xl text-primary tracking-tighter">
              {persona.name}
            </h3>
            <span className="font-mono text-label-mono text-tertiary-fixed-dim uppercase tracking-widest shrink-0">
              {persona.tagline}
            </span>
          </div>
          <p className="font-sans text-body-sm text-on-surface-variant mb-6 min-h-[2.5em]">
            {persona.description}
          </p>

          <div className="flex flex-wrap gap-2 mb-8">
            {persona.tags.map((t) => (
              <span
                key={t}
                className="font-mono text-label-mono px-2 py-1 border border-outline-variant text-on-surface-variant uppercase tracking-wider"
              >
                {t}
              </span>
            ))}
          </div>

          <button
            onClick={() => onSelect(persona.id)}
            className={`w-full py-4 font-mono text-label-mono uppercase tracking-widest transition-colors ${
              selected
                ? 'bg-tertiary-fixed text-on-tertiary cursor-default'
                : 'bg-transparent border border-primary text-primary hover:bg-primary hover:text-on-primary'
            }`}
            disabled={selected}
          >
            {selected ? '已激活' : '初始化身份'}
          </button>
        </div>
      </div>
    </div>
  );
}
