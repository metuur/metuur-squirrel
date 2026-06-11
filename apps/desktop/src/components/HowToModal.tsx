// "How to use Squirrel" overlay — a quick-start guide for the slash
// commands (run inside your coding agent) and the `squirrel` CLI, plus a
// link to the full README.
//
// Structurally this mirrors HandshakeBanner (header / scrollable body /
// footer), but it is informational rather than a critical block: it is
// dismissible and uses neutral chrome instead of the critical-red banner.
//
// Each command is a collapsible <details> row: collapsed it shows the
// command + a one-line summary; expanded it reveals what it does, the
// outcome, and an example invocation.
//
// Opened two ways (the parent App owns the `open` state):
//   • the in-app "?" header button, and
//   • the tray "How to use Squirrel" item, which shows the window and emits
//     a `show-how-to` event the App listens for.

import { openWebUrl } from "../api/client";

interface CommandEntry {
  cmd: string; // the command chip text
  summary: string; // one-liner shown while collapsed
  what: string; // what it does
  outcome: string; // the result you get
  example: string; // a concrete example invocation
}

const AGENT_COMMANDS: CommandEntry[] = [
  {
    cmd: "/sq-init",
    summary: "Set Squirrel up for your vault and agent",
    what: "Runs the initial setup — creates ~/.squirrel/config.toml and a minimal vault structure if you don't have one yet.",
    outcome: "Squirrel is configured and ready; your config file and a vault skeleton exist.",
    example: "/sq-init   (or /sq-init --add-vault to register another vault)",
  },
  {
    cmd: "/sq-capture",
    summary: "Jot a note or task without losing flow",
    what: "Captures a note, idea, research finding, or constraint into the vault with an auto-derived semantic tag (PROJECT-SUBAREA-NNN).",
    outcome: "A tagged note with frontmatter is written to the right folder and linked from its Project Page.",
    example: "/sq-capture pay the visa bill before June 30",
  },
  {
    cmd: "/sq-focus",
    summary: "Pick what to work on right now",
    what: "Shows or sets your manual focus pick for today, today-PM, or this week.",
    outcome: "Your chosen focus is recorded and surfaces in the popup and the Web UI.",
    example: "/sq-focus today FOO-001   (or just /sq-focus to see the current pick)",
  },
  {
    cmd: "/sq-status",
    summary: "See WIP, alerts, and a recommended focus",
    what: "Reports global vault status — work-in-progress projects, alerts, and a suggested focus. Read-only; it creates nothing.",
    outcome: "A snapshot of where everything stands right now.",
    example: "/sq-status   (or /sq-status --vault work)",
  },
  {
    cmd: "/sq-where-am-i",
    summary: "Re-orient after an interruption",
    what: "Shows the current state of all WIP projects and suggests where to pick up.",
    outcome: "A “where was I?” summary so you can resume without re-reading everything.",
    example: "/sq-where-am-i",
  },
];

const CLI_COMMANDS: CommandEntry[] = [
  {
    cmd: "squirrel status",
    summary: "WIP projects, alerts, recommended focus",
    what: "The same status report as /sq-status, straight from the terminal — it reads the vault directly, no agent needed.",
    outcome: "Prints WIP projects, alerts, and a recommended focus to your terminal.",
    example: "squirrel status   (or squirrel status --vault work)",
  },
  {
    cmd: "squirrel deadlines",
    summary: "Deadline report grouped by urgency",
    what: "Lists upcoming and overdue items grouped by urgency: overdue, critical, urgent, soon, upcoming.",
    outcome: "A prioritized deadline report you can scan at a glance.",
    example: "squirrel deadlines --level overdue,critical",
  },
  {
    cmd: "squirrel web open",
    summary: "Open the local Web UI in your browser",
    what: "Opens the local browser dashboard, starting the Web UI server first if it isn't already running.",
    outcome: "The Web UI opens in your default browser (default port 3939).",
    example: "squirrel web open",
  },
  {
    cmd: "squirrel recover",
    summary: "Find interrupted sessions to resume",
    what: "Finds recently interrupted work sessions (from the manifest or your Claude history) so you can jump back in.",
    outcome: "A list of resumable sessions within the age window (default 72 hours).",
    example: "squirrel recover --max-age 48",
  },
  {
    cmd: "squirrel install",
    summary: "Install Squirrel for your coding agent",
    what: "Installs Squirrel's commands and skills for your coding agent — Claude Code, Codex, Cursor, or Copilot (auto-detected).",
    outcome: "The slash commands become available inside your agent.",
    example: "squirrel install --agent claude",
  },
];

// Canonical docs target: the Web UI's Guide page (searchable, with FAQ) —
// not the bundled README markdown.
async function openGuide() {
  try {
    await openWebUrl("/guide");
  } catch (err) {
    console.error("[HowToModal] failed to open the Web UI guide:", err);
  }
}

// Copy-pasteable command chip — monospace, click-to-select.
function Cmd({ children }: { children: string }) {
  return (
    <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] text-ink-1 select-all whitespace-nowrap">
      {children}
    </code>
  );
}

// One collapsible command row. Native <details> keeps it dependency-free and
// accessible; the chevron rotates via the `group-open` variant.
function CommandRow({ entry }: { entry: CommandEntry }) {
  return (
    <details className="group rounded-lg border border-hairline bg-surface">
      <summary className="flex items-center gap-2.5 px-3 py-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
          className="shrink-0 text-ink-4 transition-transform duration-150 group-open:rotate-90"
        >
          <polyline points="9 6 15 12 9 18" />
        </svg>
        <Cmd>{entry.cmd}</Cmd>
        <span className="text-[12.5px] text-ink-2 truncate">{entry.summary}</span>
      </summary>
      <div className="px-3 pb-3 pt-1 pl-[33px] space-y-2 text-[12.5px] leading-relaxed text-ink-2">
        <p>
          <span className="font-semibold text-ink-1">What it does — </span>
          {entry.what}
        </p>
        <p>
          <span className="font-semibold text-ink-1">Outcome — </span>
          {entry.outcome}
        </p>
        <div>
          <span className="font-semibold text-ink-1">Example</span>
          <div className="mt-1">
            <Cmd>{entry.example}</Cmd>
          </div>
        </div>
      </div>
    </details>
  );
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
            Tap a command to see what it does, the outcome, and an example.
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
          <div className="space-y-2">
            {AGENT_COMMANDS.map((e) => (
              <CommandRow key={e.cmd} entry={e} />
            ))}
          </div>
        </section>

        {/* CLI — direct terminal access, no agent required. */}
        <section className="space-y-2.5">
          <h3 className="eyebrow">In the terminal</h3>
          <p className="text-[12.5px] leading-relaxed text-ink-2">
            The <Cmd>squirrel</Cmd> CLI reads your vault directly — no agent
            needed:
          </p>
          <div className="space-y-2">
            {CLI_COMMANDS.map((e) => (
              <CommandRow key={e.cmd} entry={e} />
            ))}
          </div>
        </section>
      </div>

      <footer className="shrink-0 flex items-center justify-between gap-2 px-4 py-3 border-t border-hairline bg-surface-2">
        <button
          type="button"
          onClick={() => void openGuide()}
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
