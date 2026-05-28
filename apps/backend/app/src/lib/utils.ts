/** Simple class-name combiner — replaces clsx + twMerge, both removed. */
export function cn(...inputs: Array<string | false | null | undefined>): string {
  return inputs.filter(Boolean).join(' ');
}

/** Format an epoch-seconds mtime as "3 days ago" / "yesterday" / "just now". */
export function fromNow(epochSeconds: number | string | null | undefined): string {
  if (epochSeconds == null || epochSeconds === '') return '';
  const seconds = typeof epochSeconds === 'string' ? parseFloat(epochSeconds) : epochSeconds;
  if (!isFinite(seconds)) return '';
  const diff = Math.floor(Date.now() / 1000 - seconds);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 2) return 'yesterday';
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} days ago`;
  const d = new Date(seconds * 1000);
  return d.toLocaleDateString();
}
