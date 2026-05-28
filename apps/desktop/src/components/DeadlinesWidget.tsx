// Phase 2 DeadlinesWidget — renders /api/home.pressing[].
// EARS R-2.4 (first 3 items), R-2.5 (format), R-2.6 (empty state), R-2.9 (dimmed).

import type { HomeState } from "../hooks/useHome";
import type { PressingItem } from "../api/client";

interface Props {
  home: HomeState;
  online: boolean;
}

function formatTail(item: PressingItem): string {
  if (item.is_overdue) {
    return `OVERDUE ${item.days_overdue ?? "?"}d`;
  }
  return `${item.hours_left ?? "?"}h left`;
}

export function DeadlinesWidget({ home, online }: Props) {
  const pressing = home.data?.pressing ?? [];
  const top = pressing.slice(0, 3);
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
        Pressing
      </h2>
      {top.length > 0 ? (
        <ul style={{ marginTop: 6, marginBottom: 0, paddingLeft: 0, listStyle: "none" }}>
          {top.map((item) => (
            <li key={item.id} style={{ fontSize: 12, color: "#f1f5f9", marginTop: 4, lineHeight: 1.35 }}>
              <span style={{ color: item.is_overdue ? "#fca5a5" : "#fbbf24", fontWeight: 600 }}>{formatTail(item)}</span>
              {" — "}
              <span>{item.title}</span>
            </li>
          ))}
        </ul>
      ) : home.data ? (
        <div style={{ marginTop: 6, fontSize: 13, color: "#94a3b8" }}>Nothing pressing today.</div>
      ) : (
        <div style={{ marginTop: 6, fontSize: 13, color: "#94a3b8" }}>—</div>
      )}
    </section>
  );
}
