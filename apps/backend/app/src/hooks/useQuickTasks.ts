import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type QuickTasksPayload } from '@/api/client';

// Web counterpart of the desktop useQuickTasks hook. No Tauri event channel in
// the browser, so we poll and refetch after each action.
const POLL_MS = 60_000;

export interface QuickTasksHook {
  data: QuickTasksPayload | null;
  reload: () => Promise<void>;
  complete: (id: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  snooze: (id: string, until: string) => Promise<void>;
}

export function useQuickTasks(enabled: boolean): QuickTasksHook {
  const [data, setData] = useState<QuickTasksPayload | null>(null);
  const mountedRef = useRef(true);

  const reload = useCallback(async () => {
    try {
      const fresh = await api.quickTasks();
      if (mountedRef.current) setData(fresh);
    } catch {
      // backend may be unreachable
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (!enabled) return;
    void reload();
    const id = window.setInterval(() => void reload(), POLL_MS);
    return () => {
      mountedRef.current = false;
      window.clearInterval(id);
    };
  }, [enabled, reload]);

  const complete = useCallback(async (id: string) => {
    await api.quickTaskComplete(id);
    await reload();
  }, [reload]);

  const remove = useCallback(async (id: string) => {
    await api.quickTaskDelete(id);
    await reload();
  }, [reload]);

  const snooze = useCallback(async (id: string, until: string) => {
    await api.quickTaskSnooze(id, until);
    await reload();
  }, [reload]);

  return { data, reload, complete, remove, snooze };
}
