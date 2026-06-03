// "How to use Squirrel" overlay — a quick-start guide for the slash
// commands (run inside your coding agent) and the `squirrel` CLI, plus a
// link to the full README.
//
// Structurally this mirrors HandshakeBanner (header / scrollable body /
// footer), but it is informational rather than a critical block: it is
// dismissible and uses neutral chrome instead of the critical-red banner.
//
// Opened two ways (the parent App owns the `open` state):
//   • the in-app "?" header button, and
//   • the tray "How to use Squirrel" item, which shows the window and emits
//     a `show-how-to` event the App listens for.

import { openPath } from "@tauri-apps/plugin-opener";
import { resolveResource } from "@tauri-apps/api/path";

// Copy-pasteable command chip — monospace, click-to-select.
function Cmd({ children }: { children: string }) {
  return (
    <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] text-ink-1 select-all whitespace-nowrap">
      {children}
    </code>
  );
}

// One command row: the command chip on the left, a one-line description.
function Row({ cmd, desc }: { cmd: string; desc: string }) {
  return (
    <li className="flex items-baseline gap-2.5">
      <Cmd>{cmd}</Cmd>
      <span className="text-[12.5px] leading-relaxed text-ink-2">{desc}</span>
    </li>
  );
}

// README is bundled as a Tauri resource (see tauri.conf.json `resources`).
// Opening it hands off to the OS default handler for Markdown. Best-effort:
// a missing handler / resource is logged, never thrown, so the overlay stays
// usable.
async function openReadme() {
  try {
    const path = await resolveResource("README.md");
    await openPath(path);
  } catch (err) {
    console.error("[HowToModal] failed to open README:", err);
  }
}

export function HowToModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="How to use Squirrel"
      className="fixed inset-0 z-50 flex flex-col items-stretch bg-surface"
    >
      {/* Header — neutral/info, distinct from the critical handshake banner. */}
      <div
        className="flex items-start gap-3 bg-surface-2 px-4 py-3"
        style={{ borderBottom: "1px solid var(--color-hairline)" }}
      >
        <span aria-hidden className="text-accent text-[18px] leading-none mt-0.5">
          ☰
        </span>
        <div className="min-w-0">
          <h2 className="text-[14px] font-semibold text-ink-1">How to use Squirrel</h2>
          <p className="text-[12px] text-ink-3 mt-0.5">
            A quick guide to the slash commands and the CLI.
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {/* Slash commands — run inside your coding agent (Claude Code, etc.). */}
        <section className="space-y-2.5">
          <h3 className="eyebrow">In your coding agent</h3>
          <p className="text-[12.5px] leading-relaxed text-ink-2">
            Type these slash commands in Claude Code (or your configured agent)
            to capture, focus, and stay oriented:
          </p>
          <ul className="space-y-2">
            <Row cmd="/sq-init" desc="Set Squirrel up for your vault and agent" />
            <Row cmd="/sq-capture" desc="Jot a note or task without losing flow" />
            <Row cmd="/sq-focus" desc="Pick what to work on right now" />
            <Row cmd="/sq-status" desc="See WIP, alerts, and a recommended focus" />
            <Row cmd="/sq-where-am-i" desc="Re-orient after an interruption" />
          </ul>
        </section>

        {/* CLI — direct terminal access, no agent required. */}
        <section className="space-y-2.5">
          <h3 className="eyebrow">In the terminal</h3>
          <p className="text-[12.5px] leading-relaxed text-ink-2">
            The <Cmd>squirrel</Cmd> CLI reads your vault directly — no agent
            needed:
          </p>
          <ul className="space-y-2">
            <Row cmd="squirrel status" desc="WIP projects, alerts, recommended focus" />
            <Row cmd="squirrel deadlines" desc="Deadline report grouped by urgency" />
            <Row cmd="squirrel web open" desc="Open the local Web UI in your browser" />
            <Row cmd="squirrel recover" desc="Find interrupted sessions to resume" />
            <Row cmd="squirrel install" desc="Install Squirrel for your coding agent" />
          </ul>
        </section>
      </div>

      <footer className="shrink-0 flex items-center justify-between gap-2 px-4 py-3 border-t border-hairline bg-surface-2">
        <button
          type="button"
          onClick={() => void openReadme()}
          className="btn"
          style={{ padding: "4px 12px", fontSize: 12 }}
        >
          Open the full guide
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            aria-hidden
          >
            <line x1="7" y1="17" x2="17" y2="7" />
            <polyline points="7 7 17 7 17 17" />
          </svg>
        </button>
        <button
          type="button"
          onClick={onClose}
          className="btn btn-primary"
          style={{ padding: "4px 12px", fontSize: 12 }}
        >
          Got it
        </button>
      </footer>
    </div>
  );
}
