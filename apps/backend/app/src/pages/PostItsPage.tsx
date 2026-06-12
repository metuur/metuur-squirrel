import { useEffect, useRef, useState } from "react";
import { ApiError, PostIt, PostItLayout, api } from "@/api/client";
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

// ── PostItPopover ─────────────────────────────────────────────────────────────

interface PostItPopoverProps {
  item: PostIt & { layout: PostItLayout };
  onClose: () => void;
  onUpdate: (id: string, fields: Partial<PostIt>) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
}

function PostItPopover({ item, onClose, onUpdate, onArchive, onDelete }: PostItPopoverProps) {
  const [text, setText] = useState(item.text);
  const [color, setColor] = useState(item.color);
  const [label, setLabel] = useState(item.label);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const [showConvert, setShowConvert] = useState(false);
  const [convertTarget, setConvertTarget] = useState<"quick_task" | "project_task" | "project_note">("quick_task");
  const [convertProjectSlug, setConvertProjectSlug] = useState("");
  const [projects, setProjects] = useState<{ slug: string; name: string }[]>([]);
  const [convertError, setConvertError] = useState<string | null>(null);
  const [convertBusy, setConvertBusy] = useState(false);

  // Load projects when showing convert UI for project targets
  useEffect(() => {
    if (showConvert && convertTarget !== "quick_task") {
      api.projectsList().then(setProjects).catch(() => {});
    }
  }, [showConvert, convertTarget]);

  const handleConvert = async () => {
    setConvertBusy(true);
    setConvertError(null);
    try {
      const slug = convertTarget !== "quick_task" ? convertProjectSlug : undefined;
      await api.postItConvert(item.id, convertTarget, slug);
      onDelete(item.id); // remove from active wall
      onClose();
    } catch (err: unknown) {
      // R-6.6: cap-full guidance
      if (err instanceof ApiError && err.status === 409) {
        setConvertError("Quick Task stack is full — complete one first.");
      } else {
        setConvertError(err instanceof Error ? err.message : "Conversion failed.");
      }
    } finally {
      setConvertBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    try {
      await api.postItUpdate(item.id, { text, color, label });
      onUpdate(item.id, { text, color, label });
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setBusy(false);
    }
  };

  const togglePin = async () => {
    await api.postItUpdate(item.id, { pinned: !item.pinned });
    onUpdate(item.id, { pinned: !item.pinned });
    onClose();
  };

  const archive = async () => {
    await api.postItArchive(item.id);
    onArchive(item.id);
    onClose();
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    await api.postItDelete(item.id);
    onDelete(item.id);
    onClose();
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.3)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: "relative",
          background: "#fff",
          borderRadius: 12,
          padding: 24,
          minWidth: 420,
          maxWidth: 540,
          width: "90vw",
          boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
        }}
        onClick={e => e.stopPropagation()}
      >
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          rows={6}
          style={{
            width: "100%",
            padding: 8,
            border: "1px solid #d1d5db",
            borderRadius: 6,
            fontFamily: "Caveat, cursive",
            fontSize: 16,
            boxSizing: "border-box",
          }}
        />
        {/* Color swatches */}
        <div style={{ display: "flex", gap: 4, margin: "8px 0" }}>
          {Object.keys(COLOR_MAP).map(c => (
            <button
              key={c}
              type="button"
              onClick={() => setColor(c)}
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: COLOR_MAP[c],
                border: color === c ? "2px solid #374151" : "2px solid transparent",
                cursor: "pointer",
              }}
            />
          ))}
        </div>
        <input
          value={label}
          onChange={e => setLabel(e.target.value)}
          placeholder="Corner label (optional)"
          style={{
            width: "100%",
            padding: "4px 8px",
            border: "1px solid #d1d5db",
            borderRadius: 6,
            marginBottom: 8,
            boxSizing: "border-box",
          }}
        />
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={save}
            disabled={busy}
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
          >
            Save
          </button>
          <button
            onClick={togglePin}
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
          >
            {item.pinned ? "Unpin" : "Pin"}
          </button>
          <button
            onClick={archive}
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
          >
            Archive
          </button>
          {/* R-5.8: in-app confirmation, NOT window.confirm */}
          {!confirmDelete ? (
            <button
              onClick={handleDelete}
              className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold text-critical border-critical"
            >
              Delete
            </button>
          ) : (
            <span className="flex items-center gap-2">
              <span className="text-sm text-critical">Sure?</span>
              <button
                onClick={handleDelete}
                className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold text-critical border-critical"
              >
                Yes
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
              >
                Cancel
              </button>
            </span>
          )}
        </div>
        {/* R-5.6: Convert section */}
        <div style={{ marginTop: 12 }}>
          {!showConvert ? (
            <button
              onClick={() => setShowConvert(true)}
              className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
              style={{
                background: "var(--color-accent)",
                color: "#fff",
                borderColor: "var(--color-accent)",
              }}
            >
              Convert →
            </button>
          ) : (
            <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 12 }}>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                {(["quick_task", "project_task", "project_note"] as const).map(t => (
                  <button key={t} onClick={() => { setConvertTarget(t); setConvertError(null); }}
                    style={{ padding: "4px 8px", borderRadius: 4, border: "none", cursor: "pointer",
                      background: convertTarget === t ? "#1d4ed8" : "#f3f4f6",
                      color: convertTarget === t ? "#fff" : "#374151",
                      fontSize: 12 }}>
                    {t === "quick_task" ? "Quick Task" : t === "project_task" ? "Project Task" : "Project Note"}
                  </button>
                ))}
              </div>
              {convertTarget !== "quick_task" && (
                <select value={convertProjectSlug} onChange={e => setConvertProjectSlug(e.target.value)}
                  style={{ width: "100%", padding: "4px 8px", border: "1px solid #d1d5db", borderRadius: 6, marginBottom: 8 }}>
                  <option value="">Select project…</option>
                  {projects.map(p => <option key={p.slug} value={p.slug}>{p.name ?? p.slug}</option>)}
                </select>
              )}
              {convertError && <p style={{ color: "#dc2626", fontSize: 13, margin: "4px 0" }}>{convertError}</p>}
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={handleConvert} disabled={convertBusy || (convertTarget !== "quick_task" && !convertProjectSlug)}
                  style={{ background: "#1d4ed8", color: "#fff", padding: "6px 12px", borderRadius: 6, border: "none", cursor: "pointer" }}>
                  {convertBusy ? "…" : "Convert"}
                </button>
                <button onClick={() => { setShowConvert(false); setConvertError(null); }}
                  style={{ background: "#f3f4f6", padding: "6px 12px", borderRadius: 6, border: "none", cursor: "pointer" }}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="Close"
          title="Close"
          style={{
            position: "absolute",
            right: 14,
            bottom: 14,
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: "#6b7280",
            fontSize: 18,
            lineHeight: 1,
            padding: 4,
          }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}

// ── PostItCard ────────────────────────────────────────────────────────────────

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

// ── PostItComposer ────────────────────────────────────────────────────────────

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

// ── ArchivedView ──────────────────────────────────────────────────────────────

interface ArchivedViewProps {
  items: PostIt[];
  onRestore: (id: string) => void;
  onDelete: (id: string) => void;
}

function ArchivedView({ items, onRestore, onDelete }: ArchivedViewProps) {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (confirmDeleteId !== id) {
      setConfirmDeleteId(id);
      return;
    }
    await api.postItDelete(id);
    onDelete(id);
    setConfirmDeleteId(null);
  };

  const handleRestore = async (id: string) => {
    await api.postItRestore(id);
    onRestore(id);
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-12 panel border-dashed">
        <span className="material-icons text-ink-4 text-4xl">inventory_2</span>
        <p className="text-ink-3 mt-2">No archived Post-its.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, padding: "16px 0" }}>
      {items.map(item => {
        const bgColor = getColor(item.color);
        return (
          <div
            key={item.id}
            style={{
              width: 180,
              opacity: 0.7,
              borderRadius: 4,
              boxShadow: "2px 3px 8px rgba(0,0,0,0.12)",
              overflow: "hidden",
            }}
          >
            <div style={{ height: 8, background: bgColor, filter: "brightness(0.8)" }} />
            <div
              style={{
                background: bgColor,
                padding: "8px 10px 10px",
                minHeight: 70,
                position: "relative",
              }}
            >
              <p
                style={{
                  fontSize: 13,
                  lineHeight: 1.4,
                  color: "#1c1917",
                  margin: "0 0 24px",
                  wordBreak: "break-word",
                  whiteSpace: "pre-wrap",
                }}
              >
                {item.text}
              </p>
              {item.label && (
                <span
                  style={{
                    position: "absolute",
                    bottom: 4,
                    right: 6,
                    fontSize: 9,
                    color: "#57534e",
                    fontWeight: 600,
                  }}
                >
                  {item.label}
                </span>
              )}
            </div>
            <div
              style={{
                background: "rgba(0,0,0,0.05)",
                display: "flex",
                gap: 4,
                padding: "4px 6px",
                justifyContent: "flex-end",
              }}
            >
              <button
                onClick={() => handleRestore(item.id)}
                style={{
                  fontSize: 11,
                  padding: "2px 6px",
                  borderRadius: 4,
                  border: "none",
                  background: "#e0f2fe",
                  color: "#0369a1",
                  cursor: "pointer",
                }}
              >
                Restore
              </button>
              {/* R-5.8: in-app confirmation, NOT window.confirm */}
              {confirmDeleteId !== item.id ? (
                <button
                  onClick={() => handleDelete(item.id)}
                  style={{
                    fontSize: 11,
                    padding: "2px 6px",
                    borderRadius: 4,
                    border: "none",
                    background: "#fee2e2",
                    color: "#dc2626",
                    cursor: "pointer",
                  }}
                >
                  Delete
                </button>
              ) : (
                <span style={{ display: "flex", gap: 2, alignItems: "center" }}>
                  <button
                    onClick={() => handleDelete(item.id)}
                    style={{
                      fontSize: 11,
                      padding: "2px 6px",
                      borderRadius: 4,
                      border: "none",
                      background: "#dc2626",
                      color: "#fff",
                      cursor: "pointer",
                    }}
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setConfirmDeleteId(null)}
                    style={{
                      fontSize: 11,
                      padding: "2px 6px",
                      borderRadius: 4,
                      border: "none",
                      background: "#f3f4f6",
                      cursor: "pointer",
                    }}
                  >
                    No
                  </button>
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── PostItsPage ───────────────────────────────────────────────────────────────

export default function PostItsPage() {
  const { data, loading, error, setData } = usePostIts();
  const containerRef = useRef<HTMLDivElement>(null);
  const [openCardId, setOpenCardId] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [archivedItems, setArchivedItems] = useState<PostIt[]>([]);
  const [archivedLoading, setArchivedLoading] = useState(false);

  const active = data.filter(it => it.state !== "archived");

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

  // Popover callbacks
  const handleUpdate = (id: string, fields: Partial<PostIt>) => {
    setData(prev => prev.map(item => item.id === id ? { ...item, ...fields } : item));
  };

  const handleArchive = (id: string) => {
    // Remove from active wall (filter to state !== "archived" already handles display,
    // but we update state so archived panel picks it up if open)
    setData(prev => prev.map(item => item.id === id ? { ...item, state: "archived" } : item));
    if (showArchived) {
      const archived = data.find(it => it.id === id);
      if (archived) {
        setArchivedItems(prev => [{ ...archived, state: "archived" }, ...prev]);
      }
    }
  };

  const handleDelete = (id: string) => {
    setData(prev => prev.filter(item => item.id !== id));
    setArchivedItems(prev => prev.filter(item => item.id !== id));
  };

  // Archived panel
  const toggleArchived = async () => {
    const next = !showArchived;
    setShowArchived(next);
    if (next && archivedItems.length === 0) {
      setArchivedLoading(true);
      try {
        const all = await api.postItsList(true);
        setArchivedItems(all.filter(it => it.state === "archived"));
      } catch (err) {
        console.error("Failed to load archived Post-its", err);
      } finally {
        setArchivedLoading(false);
      }
    }
  };

  const handleRestore = (id: string) => {
    const restored = archivedItems.find(it => it.id === id);
    setArchivedItems(prev => prev.filter(it => it.id !== id));
    if (restored) {
      // Add back to active wall with layout
      const withLayout = restored.layout ?? defaultLayout(restored.id, data.length);
      setData(prev => [...prev, { ...restored, state: "active", layout: withLayout }]);
    }
  };

  const handleArchivedDelete = (id: string) => {
    setArchivedItems(prev => prev.filter(it => it.id !== id));
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

  const openItem = openCardId
    ? data.find(it => it.id === openCardId)
    : null;
  const openItemWithLayout = openItem
    ? { ...openItem, layout: openItem.layout ?? defaultLayout(openItem.id, 0) }
    : null;

  return (
    <div style={{ minHeight: "calc(100vh - 4rem)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <h1 className="title">Post-its</h1>
        <button
          onClick={toggleArchived}
          style={{
            padding: "6px 14px",
            borderRadius: 6,
            border: "1px solid #d1d5db",
            background: showArchived ? "#374151" : "#fff",
            color: showArchived ? "#fff" : "#374151",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          {showArchived ? "Hide archived" : "Show archived"}
        </button>
      </div>

      {/* Archived panel — R-5.7 */}
      {showArchived && (
        <div style={{ marginBottom: 24, background: "#f9fafb", borderRadius: 8, padding: "12px 16px", border: "1px solid #e5e7eb" }}>
          <p style={{ fontWeight: 600, fontSize: 13, color: "#6b7280", marginBottom: 8 }}>Archived</p>
          {archivedLoading ? (
            <div className="animate-pulse" style={{ height: 60 }} />
          ) : (
            <ArchivedView
              items={archivedItems}
              onRestore={handleRestore}
              onDelete={handleArchivedDelete}
            />
          )}
        </div>
      )}

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
          {active.map(item => (
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

      {/* Popover — R-5.5 */}
      {openCardId && openItemWithLayout && (
        <PostItPopover
          item={openItemWithLayout}
          onClose={() => setOpenCardId(null)}
          onUpdate={handleUpdate}
          onArchive={handleArchive}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
