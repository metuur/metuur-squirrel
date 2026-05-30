import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { api, type NotificationItem } from "../api/client";

export interface NotificationsState {
  items: NotificationItem[];
  unreadCount: number;
}

export interface NotificationsHook extends NotificationsState {
  markAllRead: () => Promise<void>;
  dismiss: (id: number) => Promise<void>;
  loadAll: () => Promise<void>;
}

export function useNotifications(): NotificationsHook {
  const [state, setState] = useState<NotificationsState>({
    items: [],
    unreadCount: 0,
  });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let unlisten: (() => void) | null = null;
    let cancelled = false;

    const fetchUnread = async () => {
      try {
        const data = await api.notifications({ limit: 3, unread: true });
        if (!mountedRef.current) return;
        setState({ items: data.items, unreadCount: data.unread_count });
      } catch {
        // backend may not be running yet
      }
    };

    // Populate immediately so the panel shows on popup open (R-6.2 covers event-driven refetch).
    void fetchUnread();

    // R-6.1: register on mount, unregister on unmount.
    listen<number>("squirrel:notif-updated", () => {
      void fetchUnread();
    }).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });

    return () => {
      mountedRef.current = false;
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  // R-6.3: markAllRead — POST read-all, then clear local state.
  const markAllRead = useCallback(async () => {
    await api.notificationsMarkAllRead();
    if (!mountedRef.current) return;
    setState({ items: [], unreadCount: 0 });
  }, []);

  // R-6.3: dismiss — optimistic remove, then PATCH.
  const dismiss = useCallback(async (id: number) => {
    setState((prev) => ({
      items: prev.items.filter((item) => item.id !== id),
      unreadCount: Math.max(0, prev.unreadCount - 1),
    }));
    await api.notificationDismiss(id);
  }, []);

  // R-6.4: loadAll — fetch without limit or unread filters.
  const loadAll = useCallback(async () => {
    try {
      const data = await api.notifications({});
      if (!mountedRef.current) return;
      setState({ items: data.items, unreadCount: data.unread_count });
    } catch {
      // backend may not be running yet
    }
  }, []);

  return { ...state, markAllRead, dismiss, loadAll };
}
