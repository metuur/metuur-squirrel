import { useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import type { NotificationsHook } from "../hooks/useNotifications";
import type { NotificationItem } from "../api/client";

interface Props {
  notifications: NotificationsHook;
  open: boolean;
  onClose: () => void;
}

const TYPE_DOT: Record<string, string> = {
  pressing: "bg-red-400 dark:bg-red-500",
  reminder_active: "bg-amber-400 dark:bg-amber-500",
};

function dotColor(type: string): string {
  return TYPE_DOT[type] ?? "bg-slate-400 dark:bg-slate-500";
}

interface RowProps {
  item: NotificationItem;
  onDismiss: (id: number) => void;
}

function NotifRow({ item, onDismiss }: RowProps) {
  return (
    <li className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm px-3 py-2">
      <div className="flex items-start gap-2">
        <span
          className={`mt-1 shrink-0 h-2 w-2 rounded-full ${dotColor(item.type)}`}
          aria-hidden
        />
        <p className="flex-1 min-w-0 text-xs font-semibold text-slate-800 dark:text-slate-200 leading-snug truncate">
          {item.title}
        </p>
      </div>
      {item.body && (
        <p className="mt-0.5 ml-4 text-[11px] text-slate-500 dark:text-slate-400 leading-snug truncate">
          {item.body}
        </p>
      )}
      <div className="mt-1.5 ml-4 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => item.item_url && void openUrl(item.item_url)}
          disabled={!item.item_url}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-primary hover:text-white hover:border-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Go to →
        </button>
        <button
          type="button"
          onClick={() => onDismiss(item.id)}
          aria-label="Dismiss notification"
          className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 text-base leading-none transition-colors"
        >
          ✕
        </button>
      </div>
    </li>
  );
}

export function NotificationCenter({ notifications, open, onClose }: Props) {
  const { items, unreadCount, markAllRead, dismiss, loadAll } = notifications;
  const [showAll, setShowAll] = useState(false);

  if (!open || unreadCount === 0) return null;

  const handleViewAll = () => {
    setShowAll(true);
    void loadAll();
  };

  const hasMore = !showAll && unreadCount > items.length;

  return (
    <>
      {/* Backdrop — closes modal on outside click */}
      <div className="fixed inset-0 z-40" onClick={onClose} />

      {/* Notification panel */}
      <div className="fixed inset-x-3 top-12 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl">
        <div className="px-4 pt-3 pb-3">
          <div className="flex items-center justify-between border-b-2 border-amber-300 dark:border-amber-700/50 pb-1 mb-1.5 px-0.5">
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Notifications
            </h3>
            <span className="inline-flex items-center justify-center min-w-5 h-5 px-1.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-[10px] font-bold rounded-full">
              {unreadCount}
            </span>
          </div>

          <ul className="space-y-1.5">
            {items.map((item) => (
              <NotifRow key={item.id} item={item} onDismiss={dismiss} />
            ))}
          </ul>

          <div className="mt-2 flex items-center justify-between gap-2">
            {hasMore ? (
              <button
                type="button"
                onClick={handleViewAll}
                className="text-[11px] text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 underline-offset-2 hover:underline"
              >
                View all ({unreadCount})
              </button>
            ) : (
              <span />
            )}
            <button
              type="button"
              onClick={() => void markAllRead()}
              className="text-[11px] text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 underline-offset-2 hover:underline"
            >
              Mark all read
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
