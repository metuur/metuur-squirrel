// Phase 2 FocusWidget — renders /api/home.focus.
// EARS R-2.2 (render), R-2.3 (null focus), R-2.9 (dimmed when offline).

import type { HomeState } from "../hooks/useHome";

interface Props {
  home: HomeState;
  online: boolean;
}

export function FocusWidget({ home, online }: Props) {
  const focus = home.data?.focus ?? null;
  const dimmed = !online;

  return (
    <section
      style={{
        padding: "12px 14px",
        borderBottom: "1px solid #1f2937",
        opacity: dimmed ? 0.5 : 1,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h2 style={{ margin: 0, fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "#94a3b8" }}>
        Today's focus
      </h2>
      {focus ? (
        <>
          <div style={{ marginTop: 6, fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>{focus.title}</div>
          <div style={{ marginTop: 2, fontSize: 12, color: "#cbd5e1" }}>{focus.next_action}</div>
        </>
      ) : home.data ? (
        <div style={{ marginTop: 6, fontSize: 13, color: "#94a3b8" }}>
          No active focus — capture a thought or start a project.
        </div>
      ) : (
        <div style={{ marginTop: 6, fontSize: 13, color: "#94a3b8" }}>—</div>
      )}
    </section>
  );
}
