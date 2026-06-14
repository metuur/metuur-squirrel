// Mind Journal check-in — fully in-app (the popup never opens the web UI for
// journaling). Two prompts + mood, appended to the journal task via
// POST /api/journal/entry; recent entries listed below.

import { useEffect, useState } from "react";
import { api, type JournalEntry, type Mood } from "../api/client";
import { useToast } from "./Toast";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Called after a successful entry so the parent can refresh home (clears
   *  the brain "due" dot). */
  onLogged?: () => void;
}

const BACKDROP_STYLE: React.CSSProperties = {
  background: "rgba(14, 17, 22, 0.45)",
};

const MOODS: { value: Mood; emoji: string; label: string }[] = [
  { value: "happy", emoji: "😊", label: "Happy" },
  { value: "neutral", emoji: "😐", label: "Neutral" },
  { value: "sad", emoji: "😔", label: "Sad" },
];
const MOOD_EMOJI: Record<Mood, string> = { happy: "😊", neutral: "😐", sad: "😔" };

export function JournalModal({ open, onClose, onLogged }: Props) {
  const [mind, setMind] = useState("");
  const [doing, setDoing] = useState("");
  const [mood, setMood] = useState<Mood>("neutral");
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [exists, setExists] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    setError(null);
    setMind("");
    setDoing("");
    setMood("neutral");
    api
      .journal()
      .then((j) => {
        setExists(j.exists);
        setEntries(j.entries ?? []);
      })
      .catch(() => {
        /* keep modal usable; submit will surface errors */
      });
  }, [open]);

  if (!open) return null;

  // Require at least 3 chars in either prompt so empty check-ins can't be
  // logged (mirrors the web JournalPage rule).
  const canSave = mind.trim().length >= 3 || doing.trim().length >= 3;

  const handleCreate = async () => {
    if (creating) return;
    setCreating(true);
    setError(null);
    try {
      const j = await api.journalCreate();
      setExists(j.exists);
      setEntries(j.entries ?? []);
      toast.show("Mind Journal created.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  };

  const handleSave = async () => {
    if (saving || !canSave) return;
    setSaving(true);
    setError(null);
    try {
      await api.journalEntry({ mind: mind.trim(), doing: doing.trim(), mood });
      setSaving(false);
      onClose();
      onLogged?.();
      toast.show("Journal entry saved.");
    } catch (err) {
      setSaving(false);
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
      style={BACKDROP_STYLE}
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving) onClose();
      }}
    >
      <div className="panel w-full max-w-sm flex flex-col" style={{ maxHeight: "calc(100vh - 4rem)" }}>
        <div className="px-4 py-3 border-b border-hairline flex items-center gap-2">
          <span aria-hidden>🧠</span>
          <h2 className="title text-sm">Mind Journal</h2>
        </div>

        {!exists ? (
          <div className="px-4 py-6 flex flex-col items-center gap-3 text-center">
            <p className="text-ink-3 text-xs">
              No Mind Journal here — it was removed. That's fine.
            </p>
            <button
              type="button"
              onClick={handleCreate}
              disabled={creating}
              className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? "Adding…" : "Add Journal"}
            </button>
          </div>
        ) : (
          <>
            <div className="px-4 py-3 flex flex-col gap-3 overflow-y-auto">
              {error && (
                <div
                  className="bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px]"
                  style={{ border: "1px solid rgba(200, 54, 42, 0.25)" }}
                >
                  {error}
                </div>
              )}

              <label className="flex flex-col gap-1">
                <span className="eyebrow text-ink-2">What is your mind thinking right now?</span>
                <textarea
                  value={mind}
                  onChange={(e) => setMind(e.target.value)}
                  rows={2}
                  disabled={saving}
                  placeholder="Let it out…"
                  className="bg-surface-2 text-ink border border-hairline rounded-lg px-2.5 py-2 text-xs resize-none outline-none disabled:opacity-50 focus:border-accent"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="eyebrow text-ink-2">What are you doing right now?</span>
                <textarea
                  value={doing}
                  onChange={(e) => setDoing(e.target.value)}
                  rows={2}
                  disabled={saving}
                  placeholder="The activity…"
                  className="bg-surface-2 text-ink border border-hairline rounded-lg px-2.5 py-2 text-xs resize-none outline-none disabled:opacity-50 focus:border-accent"
                />
              </label>

              <div className="flex flex-col gap-1">
                <span className="eyebrow text-ink-2">How do you feel?</span>
                <div className="flex gap-2">
                  {MOODS.map((m) => (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setMood(m.value)}
                      aria-pressed={mood === m.value}
                      className={`flex-1 rounded-lg border px-2 py-2 text-center transition-all ${
                        mood === m.value
                          ? "border-accent bg-surface-2"
                          : "border-hairline hover:border-ink-4"
                      }`}
                    >
                      <div className="text-xl leading-none">{m.emoji}</div>
                      <div className="text-[10px] text-ink-3 mt-0.5">{m.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {entries.length > 0 && (
                <div className="flex flex-col gap-1.5 pt-1">
                  <span className="eyebrow text-ink-2">Recent</span>
                  {entries.slice(-5).reverse().map((entry, i) => (
                    <div
                      key={`${entry.timestamp}-${i}`}
                      className="bg-surface-2 border border-hairline-2 rounded-lg px-2.5 py-1.5"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm leading-none">{MOOD_EMOJI[entry.mood] ?? "·"}</span>
                        <span className="text-[10px] font-mono text-ink-4">{entry.timestamp}</span>
                      </div>
                      {entry.mind && (
                        <p className="text-[11px] text-ink mt-0.5 leading-snug">{entry.mind}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="px-4 py-3 bg-surface-2 border-t border-hairline-2 flex items-center justify-end gap-2">
              <button type="button" onClick={onClose} disabled={saving} className="btn btn-ghost disabled:opacity-50">
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !canSave}
                className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? "Saving…" : "Log this moment"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
