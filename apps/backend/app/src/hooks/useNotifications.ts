import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type NotificationItem } from '@/api/client';

export interface NotificationsState {
  items: NotificationItem[];
  unreadCount: number;
}

export interface NotificationsHook extends NotificationsState {
  markAllRead: () => Promise<void>;
  dismiss: (id: number) => Promise<void>;
  loadAll: () => Promise<void>;
}

// Web counterpart of the desktop useNotifications hook. The desktop popup
// refetches off a Tauri "squirrel:notif-updated" event; the browser has no such
// channel, so we poll every 2 minutes instead and refetch on mount.
const POLL_MS = 120_000;

export function useNotifications(): NotificationsHook {
  const [state, setState] = useState<NotificationsState>({ items: [], unreadCount: 0 });
  const mountedRef = useRef(true);

  const fetchUnread = useCallback(async () => {
    try {
      const data = await api.notifications({ limit: 5, unread: true });
      if (!mountedRef.current) return;
      setState({ items: data.items, unreadCount: data.unread_count });
    } catch {
      // backend may not be reachable yet
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void fetchUnread();
    const id = window.setInterval(() => void fetchUnread(), POLL_MS);
    return () => {
      mountedRef.current = false;
      window.clearInterval(id);
    };
  }, [fetchUnread]);

  const markAllRead = useCallback(async () => {
    await api.notificationsMarkAllRead();
    if (!mountedRef.current) return;
    setState({ items: [], unreadCount: 0 });
  }, []);

  const dismiss = useCallback(async (id: number) => {
    setState((prev) => ({
      items: prev.items.filter((item) => item.id !== id),
      unreadCount: Math.max(0, prev.unreadCount - 1),
    }));
    await api.notificationDismiss(id);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      const data = await api.notifications({});
      if (!mountedRef.current) return;
      setState({ items: data.items, unreadCount: data.unread_count });
    } catch {
      // backend may not be reachable yet
    }
  }, []);

  return { ...state, markAllRead, dismiss, loadAll };
}
