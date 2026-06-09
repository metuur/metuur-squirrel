import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { api, type QuickTasksPayload } from "../api/client";

export interface QuickTasksHook {
  data: QuickTasksPayload | null;
  loading: boolean;
  reload: () => Promise<void>;
  complete: (id: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  snooze: (id: string, until: string) => Promise<void>;
}

const EMPTY: QuickTasksPayload = {
  active: [],
  snoozed: [],
  active_count: 0,
  snoozed_count: 0,
  limit: 5,
  return_blocked: false,
};

/**
 * Owns the Quick Task Stack for the widget (R-5.3).
 *
 * Fetches `/api/quick-tasks` on mount, whenever `refreshSignal` changes, and on
 * the daemon's `squirrel:notif-updated` event (E.3). Each action calls its
 * endpoint and reloads so the stack reflects freed/added slots.
 */
export function useQuickTasks(refreshSignal: number): QuickTasksHook {
  const [data, setData] = useState<QuickTasksPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const mountedRef = useRef(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const fresh = await api.quickTasks();
      if (mountedRef.current) setData(fresh);
    } catch {
      // backend may be offline; keep the last known state
      if (mountedRef.current && !data) setData(EMPTY);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [data]);

  // Mount + refreshSignal-driven fetch.
  useEffect(() => {
    mountedRef.current = true;
    void reload();
    return () => {
      mountedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshSignal]);

  // E.3: refetch when the daemon reports a notification change (poll cycle).
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    listen("squirrel:notif-updated", () => {
      void reload();
    }).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });
    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  return { data, loading, reload, complete, remove, snooze };
}
