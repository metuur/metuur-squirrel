// Compact "time ago" formatter. Input is a unix epoch in **seconds** (the
// backend sends Python's `os.path.getmtime` which is a float in seconds).
// Returns short forms suitable for tight UI cards:
//   "just now" · "5m ago" · "3h ago" · "2d ago" · "5w ago" · "3mo ago" · "2y ago"
// Returns null when input is null/undefined/NaN so callers can render
// nothing instead of "Invalid".

const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;
const MONTH = 30 * DAY;
const YEAR = 365 * DAY;

export function timeAgo(epochSeconds: number | null | undefined): string | null {
  if (epochSeconds == null || !Number.isFinite(epochSeconds)) return null;
  const nowSec = Date.now() / 1000;
  const diff = Math.max(0, nowSec - epochSeconds);
  if (diff < MINUTE) return "just now";
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)}m ago`;
  if (diff < DAY) return `${Math.floor(diff / HOUR)}h ago`;
  if (diff < WEEK) return `${Math.floor(diff / DAY)}d ago`;
  if (diff < MONTH) return `${Math.floor(diff / WEEK)}w ago`;
  if (diff < YEAR) return `${Math.floor(diff / MONTH)}mo ago`;
  return `${Math.floor(diff / YEAR)}y ago`;
}
