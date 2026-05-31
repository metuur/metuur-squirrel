import { useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import type { NotificationsHook } from "../hooks/useNotifications";
import type { NotificationItem } from "../api/client";

interface Props {
  notifications: NotificationsHook;
  open: boolean;
  onClose: () => void;
}

// Notification-type dots use token-based status colors.
const TYPE_DOT_STYLE: Record<string, React.CSSProperties> = {
  pressing: { background: "var(--color-critical)" },
  reminder_active: { background: "#F1B952" }, // matches notif-badge amber
};
const DEFAULT_DOT_STYLE: React.CSSProperties = { background: "var(--color-ink-4)" };

function dotStyle(type: string): React.CSSProperties {
  return TYPE_DOT_STYLE[type] ?? DEFAULT_DOT_STYLE;
}

interface RowProps {
  item: NotificationItem;
  onDismiss: (id: number) => void;
}

function NotifRow({ item, onDismiss }: RowProps) {
  return (
    <li className="card px-3 py-2">
      <div className="flex items-start gap-2">
        <span
          className="mt-1 shrink-0 h-2 w-2 rounded-full"
          style={dotStyle(item.type)}
          aria-hidden
        />
        <p className="flex-1 min-w-0 text-xs font-semibold text-ink leading-snug truncate">
          {item.title}
        </p>
      </div>
      {item.body && (
        <p className="mt-0.5 ml-4 text-[11px] text-ink-3 leading-snug truncate">
          {item.body}
        </p>
      )}
      <div className="mt-1.5 ml-4 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => item.item_url && void openUrl(item.item_url)}
          disabled={!item.item_url}
          className="btn disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ padding: "4px 8px", fontSize: 10 }}
        >
          Go to →
        </button>
        <button
          type="button"
          onClick={() => onDismiss(item.id)}
          aria-label="Dismiss notification"
          className="text-ink-4 hover:text-ink-2 text-base leading-none transition-colors"
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
      {/* Backdrop — closes panel on outside click */}
      <div className="fixed inset-0 z-40" onClick={onClose} />

      {/* Notification panel */}
      <div className="fixed inset-x-3 top-12 z-50 panel">
        <div className="px-4 pt-3 pb-3">
          <div className="flex items-center justify-between mb-2 px-0.5">
            <div className="flex items-center gap-2">
              <span className="eyebrow">Notifications</span>
              <span className="chip chip-count tabular">{unreadCount}</span>
            </div>
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
                className="text-[11px] text-ink-3 hover:text-ink underline-offset-2 hover:underline"
              >
                View all ({unreadCount})
              </button>
            ) : (
              <span />
            )}
            <button
              type="button"
              onClick={() => void markAllRead()}
              className="text-[11px] text-ink-3 hover:text-ink underline-offset-2 hover:underline"
            >
              Mark all read
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
