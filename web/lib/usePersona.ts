'use client';

import { useCallback, useEffect, useState } from 'react';
import { mockPersonas, DEFAULT_PERSONA_ID } from '@/lib/mock';

const STORAGE_KEY = 'inkgrid:persona-id';

/**
 * 角色选择状态 hook。
 * 持久化到 localStorage，跨页面/刷新保持当前角色。
 */
export function usePersona() {
  const [personaId, setPersonaId] = useState<string>(DEFAULT_PERSONA_ID);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && mockPersonas.some((p) => p.id === stored)) {
        setPersonaId(stored);
      }
    } catch {
      /* SSR 或隐私模式：忽略 */
    }
    setHydrated(true);
  }, []);

  const select = useCallback((id: string) => {
    const valid = mockPersonas.some((p) => p.id === id);
    if (!valid) return;
    setPersonaId(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* 忽略写入失败 */
    }
  }, []);

  const persona = mockPersonas.find((p) => p.id === personaId) ?? mockPersonas[0];

  return { persona, personaId, select, hydrated };
}
