import { PostIt } from "@/api/client";
import { usePostIts } from "@/hooks/usePostIts";

const COLOR_MAP: Record<string, string> = {
  yellow: "#fef08a",
  pink:   "#f9a8d4",
  blue:   "#93c5fd",
  green:  "#86efac",
  orange: "#fdba74",
  purple: "#c4b5fd",
  white:  "#f8fafc",
};

function getColor(color: string): string {
  return COLOR_MAP[color] ?? COLOR_MAP.yellow;
}

interface PostItCardProps {
  item: PostIt;
}

function PostItCard({ item }: PostItCardProps) {
  const bgColor = getColor(item.color);
  const layout = item.layout ?? { x: 5, y: 5, rotation: 0, z: 1 };

  return (
    <div
      style={{
        position: "absolute",
        left: `${layout.x}%`,
        top: `${layout.y}%`,
        transform: `rotate(${layout.rotation}deg)`,
        zIndex: item.pinned ? 50 : layout.z,
        width: 180,
      }}
    >
      {/* Top strip */}
      <div
        style={{
          height: 10,
          backgroundColor: bgColor,
          filter: "brightness(0.8)",
          borderRadius: "4px 4px 0 0",
        }}
      />
      {/* Card body */}
      <div
        style={{
          backgroundColor: bgColor,
          borderRadius: "0 0 4px 4px",
          padding: "10px 12px 12px",
          boxShadow: "2px 3px 8px rgba(0,0,0,0.18)",
          minHeight: 100,
          position: "relative",
        }}
      >
        {/* Pin indicator */}
        {item.pinned && (
          <span
            style={{
              position: "absolute",
              top: 4,
              right: 6,
              fontSize: 14,
              lineHeight: 1,
            }}
            aria-label="pinned"
          >
            📌
          </span>
        )}

        {/* Body text */}
        <p
          className="post-it-text"
          style={{
            fontSize: 15,
            lineHeight: 1.45,
            color: "#1c1917",
            margin: 0,
            wordBreak: "break-word",
            whiteSpace: "pre-wrap",
          }}
        >
          {item.text}
        </p>

        {/* Corner label */}
        {item.label && (
          <span
            style={{
              position: "absolute",
              bottom: 6,
              right: 8,
              fontSize: 10,
              color: "#57534e",
              fontWeight: 600,
              letterSpacing: "0.02em",
              maxWidth: 80,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {item.label}
          </span>
        )}
      </div>
    </div>
  );
}

export default function PostItsPage() {
  const { data, loading, error } = usePostIts();
  const active = data.filter((it) => it.state !== "archived");

  if (loading) {
    return <div className="h-64 animate-pulse rounded-lg bg-surface-2" />;
  }

  if (error) {
    return (
      <div className="text-center py-12 panel border-dashed">
        <span className="material-icons text-critical text-4xl">error_outline</span>
        <p className="text-ink-3 mt-2">{error}</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "calc(100vh - 4rem)" }}>
      <h1 className="title mb-4">Post-its</h1>

      {active.length === 0 ? (
        <div className="text-center py-12 panel border-dashed">
          <span className="material-icons text-ink-4 text-4xl">sticky_note_2</span>
          <p className="text-ink-3 mt-2">No active Post-its.</p>
        </div>
      ) : (
        <div
          style={{
            position: "relative",
            minHeight: "calc(100vh - 8rem)",
            background: "#fef9ef",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {active.map((item) => (
            <PostItCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
