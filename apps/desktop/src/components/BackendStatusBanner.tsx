// Phase 2: top banner that becomes visible whenever the backend is
// unreachable. Renders nothing when online. EARS R-1.5.

import type { BackendStatus } from "../hooks/useBackend";

interface Props {
  status: BackendStatus;
}

export function BackendStatusBanner({ status }: Props) {
  if (status.online) return null;
  return (
    <div
      role="status"
      style={{
        background: "#7f1d1d",
        color: "white",
        padding: "8px 12px",
        fontSize: 13,
        fontFamily: "system-ui, sans-serif",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      Backend offline — run <code style={{ background: "rgba(0,0,0,0.25)", padding: "1px 4px", borderRadius: 3 }}>make backend-start</code> in the squirrel monorepo
    </div>
  );
}
