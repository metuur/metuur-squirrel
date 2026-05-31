// Phase 2: top banner shown whenever the backend is unreachable. Uses the
// paper-indigo critical palette — soft warning background, refined cardinal
// text, hairline-divided from the header below. EARS R-1.5.

import type { BackendStatus } from "../hooks/useBackend";

interface Props {
  status: BackendStatus;
}

export function BackendStatusBanner({ status }: Props) {
  if (status.online) return null;
  return (
    <div
      role="status"
      className="shrink-0 flex items-center gap-2 bg-critical-bg text-critical px-4 py-2 text-xs"
      style={{ borderBottom: "1px solid rgba(200, 54, 42, 0.25)" }}
    >
      <span aria-hidden className="text-critical">⚠</span>
      <span>
        Backend offline — run{" "}
        <code
          className="font-mono text-[11px] px-1.5 py-0.5 rounded text-critical"
          style={{ background: "rgba(200, 54, 42, 0.10)" }}
        >
          make backend-start
        </code>{" "}
        in the squirrel monorepo
      </span>
    </div>
  );
}
