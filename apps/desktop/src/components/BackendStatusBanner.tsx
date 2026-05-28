// Phase 2: top banner shown whenever the backend is unreachable. Style
// matches the v0.5 web UI's error chip vocabulary (red surface, mono
// code chip). EARS R-1.5.

import type { BackendStatus } from "../hooks/useBackend";

interface Props {
  status: BackendStatus;
}

export function BackendStatusBanner({ status }: Props) {
  if (status.online) return null;
  return (
    <div
      role="status"
      className="shrink-0 flex items-center gap-2 bg-red-50 dark:bg-red-900/30 border-b border-red-200 dark:border-red-900/50 text-red-800 dark:text-red-100 px-4 py-2 text-xs"
    >
      <span aria-hidden className="material-icons-fallback text-red-500 dark:text-red-300">⚠</span>
      <span>
        Backend offline — run{" "}
        <code className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/50 text-red-900 dark:text-red-100">
          make backend-start
        </code>{" "}
        in the squirrel monorepo
      </span>
    </div>
  );
}
