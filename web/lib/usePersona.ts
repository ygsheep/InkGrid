'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Persona } from '@/types';
import { mockPersonas, DEFAULT_PERSONA_ID } from '@/lib/mock';

const STORAGE_KEY = 'inkgrid:persona-id';

// 模块级缓存，避免每次组件 mount 都重新拉取
let personasPromise: Promise<Persona[]> | null = null;
let cachedPersonas: Persona[] | null = null;

async function loadPersonas(): Promise<Persona[]> {
  if (cachedPersonas) return cachedPersonas;
  if (!personasPromise) {
    personasPromise = api.getPersonas().then((res) => {
      cachedPersonas = res.items;
      return res.items;
    });
  }
  return personasPromise;
}

/**
 * 角色选择状态 hook。
 * 持久化到 localStorage，跨页面/刷新保持当前角色。
 * 角色列表从 /api/personas 拉取，失败时回退到 mock。
 */
export function usePersona() {
  const [personas, setPersonas] = useState<Persona[]>(mockPersonas);
  const [personaId, setPersonaId] = useState<string>(DEFAULT_PERSONA_ID);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await loadPersonas();
        if (cancelled) return;
        setPersonas(list);
        // 校正本地存的 personaId 是否在新列表中
        try {
          const stored = localStorage.getItem(STORAGE_KEY);
          if (stored && list.some((p) => p.id === stored)) {
            setPersonaId(stored);
          } else if (list.length > 0) {
            // 列表没有 stored id 时，默认选第一个
            setPersonaId(list[0].id);
          }
        } catch {
          /* SSR 或隐私模式：忽略 */
        }
      } catch {
        /* API 失败保持 mock */
      } finally {
        if (!cancelled) setHydrated(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const select = useCallback(
    (id: string) => {
      const valid = personas.some((p) => p.id === id);
      if (!valid) return;
      setPersonaId(id);
      try {
        localStorage.setItem(STORAGE_KEY, id);
      } catch {
        /* 忽略写入失败 */
      }
    },
    [personas],
  );

  const persona = personas.find((p) => p.id === personaId) ?? personas[0] ?? mockPersonas[0];

  return { persona, personaId, personas, select, hydrated };
}
