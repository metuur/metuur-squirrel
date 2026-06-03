import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { NotificationsHook } from '@/hooks/useNotifications';
import type { NotificationItem } from '@/api/client';

interface Props {
  notifications: NotificationsHook;
  open: boolean;
  onClose: () => void;
}

// Notification-type dots use token-based status colors (mirrors the desktop popup).
const TYPE_DOT_STYLE: Record<string, React.CSSProperties> = {
  pressing: { background: 'var(--color-critical)' },
  reminder_active: { background: '#F1B952' },
};
const DEFAULT_DOT_STYLE: React.CSSProperties = { background: 'var(--color-ink-4)' };

function dotStyle(type: string): React.CSSProperties {
  return TYPE_DOT_STYLE[type] ?? DEFAULT_DOT_STYLE;
}

// item_url is a full backend origin URL (e.g. http://127.0.0.1:3939/notes/X).
// On the web that origin is the app itself, so navigate to the path in-app.
function pathOf(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).pathname;
  } catch {
    return url.startsWith('/') ? url : null;
  }
}

interface RowProps {
  item: NotificationItem;
  onGo: (item: NotificationItem) => void;
  onDismiss: (id: number) => void;
}

function NotifRow({ item, onGo, onDismiss }: RowProps) {
  const target = pathOf(item.item_url);
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
        <p className="mt-0.5 ml-4 text-[11px] text-ink-3 leading-snug truncate">{item.body}</p>
      )}
      <div className="mt-1.5 ml-4 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onGo(item)}
          disabled={!target}
          className="btn disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ padding: '4px 8px', fontSize: 10 }}
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
  const navigate = useNavigate();

  if (!open) return null;

  const handleViewAll = () => {
    setShowAll(true);
    void loadAll();
  };

  const handleGo = (item: NotificationItem) => {
    const target = pathOf(item.item_url);
    if (!target) return;
    void notifications.dismiss(item.id);
    onClose();
    navigate(target);
  };

  const hasMore = !showAll && unreadCount > items.length;

  return (
    <>
      {/* Backdrop — closes panel on outside click */}
      <div className="fixed inset-0 z-40" onClick={onClose} />

      {/* Dropdown anchored under the bell button. */}
      <div
        className="panel absolute right-0 top-full mt-2 w-80 z-50 flex flex-col"
        style={{ maxHeight: 'calc(100vh - 5rem)' }}
      >
        <div className="flex items-center justify-between px-4 pt-3 pb-2 shrink-0">
          <div className="flex items-center gap-2">
            <span className="eyebrow">Notifications</span>
            {unreadCount > 0 && <span className="chip chip-count tabular">{unreadCount}</span>}
          </div>
        </div>

        {items.length === 0 ? (
          <div className="px-4 py-8 text-center text-ink-3 text-xs">You're all caught up.</div>
        ) : (
          <ul className="flex-1 min-h-0 overflow-y-auto space-y-1.5 px-4">
            {items.map((item) => (
              <NotifRow key={item.id} item={item} onGo={handleGo} onDismiss={dismiss} />
            ))}
          </ul>
        )}

        <div className="flex items-center justify-between gap-2 px-4 pt-2 pb-3 shrink-0">
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
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={() => void markAllRead()}
              className="text-[11px] text-ink-3 hover:text-ink underline-offset-2 hover:underline"
            >
              Mark all read
            </button>
          )}
        </div>
      </div>
    </>
  );
}
