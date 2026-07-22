'use client';

import Link from 'next/link';
import { ArrowLeft, Mic, Phone, PhoneOff } from 'lucide-react';

/**
 * 语音通话页 — 全屏沉浸式占位。
 * 接入流式 ASR/TTS + VAD 后，替换为实时通话 UI。
 */
export default function VoicePage() {
  return (
    <div className="flex-1 spatial-grid flex flex-col min-h-0">
      {/* 顶部条 */}
      <header className="border-b border-outline-variant bg-black/70 backdrop-blur-md z-40">
        <div className="mx-auto max-w-chat px-margin-mobile md:px-margin-desktop py-4 flex items-center justify-between">
          <Link
            href="/ask"
            className="flex items-center gap-2 font-mono text-label-mono text-on-surface-variant hover:text-primary uppercase tracking-widest"
          >
            <ArrowLeft size={14} />
            返回文字
          </Link>
          <span className="font-mono text-label-mono text-primary uppercase tracking-widest flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-tertiary-fixed-dim animate-pulse" />
            语音链路待激活
          </span>
          <span className="w-14" />
        </div>
      </header>

      {/* 通话区 */}
      <div className="flex-1 flex flex-col items-center justify-center px-margin-mobile relative z-10">
        <div className="w-32 h-32 border border-primary flex items-center justify-center mx-auto mb-6 relative">
          {/* inner-glow：1px 顶部白边表达层级抬升 */}
          <div className="absolute inset-0 border-t border-white/40" />
          <Mic size={40} className="text-primary" />
        </div>
        <p className="font-headline text-headline-md text-primary mb-2">
          语音通话
        </p>
        <p className="font-mono text-label-mono text-on-surface-variant mb-10 uppercase tracking-widest text-center max-w-xs">
          接入流式 ASR / TTS 后启用
          <br />
          支持实时打断与降噪
        </p>

        <div className="flex items-center gap-4">
          <button
            className="w-14 h-14 border border-outline-variant flex items-center justify-center text-on-surface-variant hover:text-primary hover:border-primary transition-colors"
            aria-label="接听"
          >
            <Phone size={20} />
          </button>
          <Link
            href="/ask"
            className="w-14 h-14 bg-error flex items-center justify-center text-on-error hover:opacity-90 transition-opacity"
            aria-label="挂断返回"
          >
            <PhoneOff size={20} />
          </Link>
        </div>
      </div>

      {/* 底部状态条 */}
      <footer className="border-t border-outline-variant bg-black z-40">
        <div className="mx-auto max-w-chat px-margin-mobile md:px-margin-desktop py-4 flex justify-between items-center">
          <span className="font-mono text-label-mono text-outline uppercase tracking-widest">
            编解码: OPUS-256K
          </span>
          <span className="font-mono text-label-mono text-outline uppercase tracking-widest">
            AES-256 已加密
          </span>
        </div>
      </footer>
    </div>
  );
}
