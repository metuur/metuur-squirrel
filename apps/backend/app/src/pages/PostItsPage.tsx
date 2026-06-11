import { useRef, useState } from "react";
import { PostIt, PostItLayout, api } from "@/api/client";
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

const COLOR_OPTIONS = ["yellow", "pink", "blue", "green", "orange", "purple", "white"];

function defaultLayout(id: string, index: number): PostItLayout {
  // Simple deterministic spread — mirrors server's _default_layout
  const h = id.split("").reduce((acc, c) => (acc * 31 + c.charCodeAt(0)) & 0xffffff, 0);
  const col = index % 4;
  const row = Math.floor(index / 4);
  return {
    x: 5 + col * 23 + (h % 7),
    y: 5 + row * 20 + (h % 5),
    rotation: (h % 7) - 3,
    z: 0,
  };
}

interface PostItCardProps {
  item: PostIt & { layout: PostItLayout };
  containerRef: React.RefObject<HTMLDivElement | null>;
  onLayoutChange: (id: string, layout: PostItLayout) => void;
  onCardClick: (id: string) => void;
}

function PostItCard({ item, containerRef, onLayoutChange, onCardClick }: PostItCardProps) {
  const bgColor = getColor(item.color);
  const layout = item.layout;

  const dragRef = useRef<{
    startX: number;
    startY: number;
    origX: number;
    origY: number;
    dragging: boolean;
  } | null>(null);

  const handlePointerDown = (e: React.PointerEvent) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      origX: layout.x,
      origY: layout.y,
      dragging: false,
    };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (!dragRef.current.dragging && Math.sqrt(dx * dx + dy * dy) > 5) {
      dragRef.current.dragging = true;
    }
    if (dragRef.current.dragging) {
      const el = e.currentTarget as HTMLElement;
      const container = containerRef.current;
      if (container) {
        const rect = container.getBoundingClientRect();
        const newX = ((e.clientX - rect.left) / rect.width) * 100;
        const newY = ((e.clientY - rect.top) / rect.height) * 100;
        el.style.left = `${newX}%`;
        el.style.top = `${newY}%`;
      }
    }
  };

  const handlePointerUp = async (e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const wasDragging = dragRef.current.dragging;
    dragRef.current = null;
    if (wasDragging) {
      const el = e.currentTarget as HTMLElement;
      const container = containerRef.current;
      if (container) {
        const rect = container.getBoundingClientRect();
        const newX = ((e.clientX - rect.left) / rect.width) * 100;
        const newY = ((e.clientY - rect.top) / rect.height) * 100;
        const newLayout = { ...layout, x: newX, y: newY };
        onLayoutChange(item.id, newLayout);
        try {
          await api.postItUpdateLayout(item.id, newLayout);
        } catch (err) {
          console.error("Failed to persist layout", err);
        }
      }
    } else {
      onCardClick(item.id);
    }
  };

  return (
    <div
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      style={{
        position: "absolute",
        left: `${layout.x}%`,
        top: `${layout.y}%`,
        transform: `rotate(${layout.rotation}deg)`,
        zIndex: item.pinned ? 50 : layout.z,
        width: 180,
        cursor: "grab",
        touchAction: "none",
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

function PostItComposer({ onCreated }: { onCreated: (item: PostIt) => void }) {
  const [text, setText] = useState("");
  const [color, setColor] = useState("yellow");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      const created = await api.postItCreate({ text: text.trim(), color });
      onCreated(created);
      setText("");
    } catch (err) {
      console.error("Failed to create Post-it", err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: "flex",
        gap: 8,
        padding: "12px 16px",
        alignItems: "center",
        background: "#fff",
        borderBottom: "1px solid #e5e7eb",
      }}
    >
      <input
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="New Post-it..."
        style={{
          flex: 1,
          padding: "6px 10px",
          border: "1px solid #d1d5db",
          borderRadius: 6,
        }}
      />
      <div style={{ display: "flex", gap: 4 }}>
        {COLOR_OPTIONS.map(c => (
          <button
            key={c}
            type="button"
            onClick={() => setColor(c)}
            style={{
              width: 20,
              height: 20,
              borderRadius: "50%",
              background: COLOR_MAP[c] ?? c,
              border: color === c ? "2px solid #374151" : "2px solid transparent",
              cursor: "pointer",
            }}
          />
        ))}
      </div>
      <button
        type="submit"
        disabled={!text.trim() || busy}
        style={{
          padding: "6px 14px",
          background: "#374151",
          color: "#fff",
          borderRadius: 6,
          border: "none",
          cursor: "pointer",
          opacity: !text.trim() ? 0.5 : 1,
        }}
      >
        Add
      </button>
    </form>
  );
}

export default function PostItsPage() {
  const { data, loading, error, setData } = usePostIts();
  const containerRef = useRef<HTMLDivElement>(null);
  const [openCardId, setOpenCardId] = useState<string | null>(null);
  const active = data.filter((it) => it.state !== "archived");

  const handleCreated = (item: PostIt) => {
    setData(prev => {
      const withLayout = item.layout ?? defaultLayout(item.id, prev.length);
      return [...prev, { ...item, layout: withLayout }];
    });
  };

  const handleLayoutChange = (id: string, layout: PostItLayout) => {
    setData(prev => prev.map(item => item.id === id ? { ...item, layout } : item));
  };

  const handleCardClick = (id: string) => {
    setOpenCardId(id);
  };

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

      <PostItComposer onCreated={handleCreated} />

      {active.length === 0 ? (
        <div className="text-center py-12 panel border-dashed">
          <span className="material-icons text-ink-4 text-4xl">sticky_note_2</span>
          <p className="text-ink-3 mt-2">No active Post-its.</p>
        </div>
      ) : (
        <div
          ref={containerRef}
          style={{
            position: "relative",
            minHeight: "calc(100vh - 8rem)",
            background: "#fef9ef",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {active.map((item) => (
            <PostItCard
              key={item.id}
              item={{ ...item, layout: item.layout ?? defaultLayout(item.id, active.indexOf(item)) }}
              containerRef={containerRef}
              onLayoutChange={handleLayoutChange}
              onCardClick={handleCardClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}
