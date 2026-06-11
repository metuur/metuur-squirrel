// Guide / tutorial page — how to use Squirrel across its three surfaces:
// your coding agent (slash commands), the `squirrel` CLI, and this Web UI.
// Static content; commands mirror agent-pack/commands/ and apps/cli/squirrel.

interface CommandEntry {
  cmd: string; // command chip text
  summary: string; // one-liner shown collapsed
  what: string; // what it does
  example: string; // concrete invocation
}

interface CommandGroup {
  title: string;
  blurb: string;
  entries: CommandEntry[];
}

const AGENT_GROUPS: CommandGroup[] = [
  {
    title: 'Set up & bring your notes',
    blurb: 'One-time steps to point Squirrel at a vault and bring existing notes in.',
    entries: [
      {
        cmd: '/sq-init',
        summary: 'First-time setup for your vault and agent',
        what: 'Creates ~/.squirrel/config.toml and a minimal vault structure if you don’t have one yet. Run it once per machine.',
        example: '/sq-init   (or /sq-init --add-vault to register another vault)',
      },
      {
        cmd: '/sq-migrate-vault',
        summary: 'Migrate an existing Obsidian vault into Squirrel',
        what: 'Scans your old vault and maps folders to projects, notes to tasks, and loose notes to the Inbox. Shows a dry-run plan first and never modifies the original vault.',
        example: '/sq-migrate-vault ~/Documents/my-old-vault',
      },
      {
        cmd: '/sq-new-project',
        summary: 'Create a project (page + optional first task)',
        what: 'Scaffolds a project folder and page in the vault, refusing to blow past the work-in-progress cap.',
        example: '/sq-new-project MYAPP --type C',
      },
    ],
  },
  {
    title: 'Daily flow',
    blurb: 'Start with context, capture as you go, shut down so tomorrow-you can resume.',
    entries: [
      {
        cmd: '/sq-start',
        summary: 'Start a session with full project context',
        what: 'Loads the latest shutdown notes, open tasks, and blockers into a short loading note, so you re-enter the project without re-reading 20 files.',
        example: '/sq-start MYAPP',
      },
      {
        cmd: '/sq-capture',
        summary: 'Jot a note or task without losing flow',
        what: 'Captures an idea, finding, or constraint into the vault with a semantic tag and links it from its project page.',
        example: '/sq-capture pay the visa bill before June 30',
      },
      {
        cmd: '/sq-focus',
        summary: 'Pick what to work on right now',
        what: 'Shows or sets your manual focus pick for today, today-PM, or this week. The pick surfaces in the desktop popup and this Web UI.',
        example: '/sq-focus today FOO-001',
      },
      {
        cmd: '/sq-status',
        summary: 'WIP, alerts, and a recommended focus',
        what: 'Read-only snapshot of every work-in-progress project, with alerts (deadlines, stale work) and a suggested focus.',
        example: '/sq-status   (or /sq-status --vault work)',
      },
      {
        cmd: '/sq-where-am-i',
        summary: 'Re-orient after an interruption',
        what: 'Shows the current state of all WIP projects and suggests where to pick up.',
        example: '/sq-where-am-i',
      },
      {
        cmd: '/sq-brief',
        summary: 'Status brief ready for Slack or email',
        what: 'Produces a 6-section brief (now / done / next / decisions / steps / context) you can paste into a stand-up or stakeholder update.',
        example: '/sq-brief MYAPP',
      },
      {
        cmd: '/sq-end',
        summary: 'Shut down a session properly',
        what: 'Writes a structured shutdown note (state, next physical action, decisions, open loops) to the active task — the thing /sq-start reads tomorrow.',
        example: '/sq-end',
      },
      {
        cmd: '/sq-recover',
        summary: 'Reconstruct context when you forgot /sq-end',
        what: 'Inspects git activity and session manifests to rebuild what you were doing in interrupted sessions.',
        example: '/sq-recover',
      },
    ],
  },
  {
    title: 'Staying on track',
    blurb: 'Deadline pressure, task paralysis, and decisions — handled in the vault.',
    entries: [
      {
        cmd: '/sq-deadlines',
        summary: 'Deadline report grouped by urgency',
        what: 'Lists overdue and upcoming items grouped by urgency, from critical to distant.',
        example: '/sq-deadlines',
      },
      {
        cmd: '/sq-reminders',
        summary: 'Set and manage date reminders on tasks',
        what: 'Lists, snoozes, or dismisses reminders. /sq-reminders-install adds the macOS background daemon that fires them as notifications.',
        example: '/sq-reminders',
      },
      {
        cmd: '/sq-chunk',
        summary: 'Break an overwhelming task into chunks',
        what: 'Decomposes a big task into focus-friendly sub-tasks sized for short attention windows.',
        example: '/sq-chunk MYAPP-AUTH-001',
      },
      {
        cmd: '/sq-task-initiation',
        summary: 'Break through task-start paralysis',
        what: 'Turns a daunting task into a tiny, concrete first physical action so starting stops being the hard part.',
        example: '/sq-task-initiation',
      },
      {
        cmd: '/sq-estimate',
        summary: 'Reality-check a time estimate',
        what: 'Applies a focus-time buffer to your estimate so plans survive contact with a real day.',
        example: '/sq-estimate 2h',
      },
      {
        cmd: '/sq-decision',
        summary: 'Capture a decision as a lightweight ADR',
        what: 'Records an architectural or design decision with context in the project, so future-you knows why.',
        example: '/sq-decision we use SQLite over Postgres for local state',
      },
    ],
  },
  {
    title: 'Work ↔ personal machines',
    blurb: 'Move context across an air gap (clipboard or email — no shared network needed).',
    entries: [
      {
        cmd: '/sq-sync-out',
        summary: 'Export a self-contained context package',
        what: 'Generates a hash-signed SQUIRREL-PACKAGE of the selected scope, scanning for sensitive content before it leaves.',
        example: '/sq-sync-out MYAPP',
      },
      {
        cmd: '/sq-sync-in',
        summary: 'Apply a package on the other machine',
        what: 'Validates and applies a SQUIRREL-PACKAGE into this vault, with compliance checks and an audit trail.',
        example: '/sq-sync-in   (then paste the package)',
      },
    ],
  },
];

const CLI_COMMANDS: CommandEntry[] = [
  {
    cmd: 'squirrel status',
    summary: 'WIP projects, alerts, recommended focus',
    what: 'The same report as /sq-status, straight from the terminal — reads the vault directly, no agent needed.',
    example: 'squirrel status   (or squirrel status --vault work)',
  },
  {
    cmd: 'squirrel deadlines',
    summary: 'Deadline report grouped by urgency',
    what: 'Prints upcoming and overdue items grouped by urgency level.',
    example: 'squirrel deadlines --level overdue,critical',
  },
  {
    cmd: 'squirrel recover',
    summary: 'Find interrupted sessions to resume',
    what: 'Finds recently interrupted work sessions from the manifest or your agent history.',
    example: 'squirrel recover --max-age 48',
  },
  {
    cmd: 'squirrel vaults',
    summary: 'Manage configured vaults',
    what: 'Lists, adds, removes, or sets the default vault in ~/.squirrel/config.toml.',
    example: 'squirrel vaults list   ·   squirrel vaults add work ~/work-vault',
  },
  {
    cmd: 'squirrel web open',
    summary: 'Open this Web UI in your browser',
    what: 'Opens the local dashboard (this app), starting the server first if it isn’t already running.',
    example: 'squirrel web open',
  },
  {
    cmd: 'squirrel install',
    summary: 'Install Squirrel for your coding agent',
    what: 'Installs the slash commands and skills for Claude Code, Codex, Cursor, or Copilot (auto-detected).',
    example: 'squirrel install --agent claude',
  },
];

const POPUP_FEATURES: [string, string, string][] = [
  [
    'keyboard_command_key',
    'Summon it anywhere',
    'Press ⌃⌘S to open the popup over whatever you’re doing; ⌃⌘Q captures a quick task without even opening it.',
  ],
  [
    'center_focus_strong',
    'Focus widget',
    'Your AM / PM / week picks, with check-in and check-out: a session timer runs while you work and banks the time into the task, with estimate-vs-actual reconciliation.',
  ],
  [
    'event',
    'Deadlines widget',
    'Pressing items at a glance, each with a “+ note” button that captures straight into that task.',
  ],
  [
    'bolt',
    'Quick Tasks & Parakeet',
    'The quick-task stack (max 5) and the parakeet — a deadline reminder whose tone matches the urgency.',
  ],
  [
    'psychology',
    'Mind Journal & notifications',
    'The brain icon shows a dot when a check-in is due; the bell collects reminders fired by the background daemon.',
  ],
  [
    'open_in_new',
    'Jump out',
    'Footer buttons open this Web UI or your vault in Obsidian; the “?” icon opens the same how-to guide in-app.',
  ],
];

const TRAY_FEATURES: [string, string, string][] = [
  [
    'menu_open',
    'Always one click away',
    'Open Squirrel, Add Quick Task, Open Web UI, Open Obsidian Vault, How to use Squirrel, Restart Service, and Quit live in the menu-bar dropdown.',
  ],
  [
    'priority_high',
    'Pressing now',
    'Items due now are listed right in the menu — click one to jump to it.',
  ],
  [
    'notifications_active',
    'On your radar / Reminder due',
    'Approaching and active reminders surface as their own menu sections as they come due.',
  ],
  [
    'bolt',
    'Quick tasks & check-ins',
    'A QUICK TASKS section appears while you have active ones, and a “🧠 Mind Journal — check in” entry shows up when a check-in is due. On macOS, notification banners aren’t clickable — the menu-bar icon is where you act on them.',
  ],
];

const CONCEPTS: { icon: string; term: string; def: string }[] = [
  {
    icon: 'folder',
    term: 'Vault',
    def: 'A plain-Markdown folder (Obsidian-compatible) that holds everything. Squirrel never locks your data in a database — every project and task is a readable .md file.',
  },
  {
    icon: 'rocket_launch',
    term: 'Project',
    def: 'A folder with a project page, e.g. MYAPP/MYAPP.md. Active projects live in 01-Active-Projects/; parked ones in the 02-Parking-Lot/.',
  },
  {
    icon: 'task_alt',
    term: 'Task (intent)',
    def: 'One outcome-sized unit of work inside a project, with a definition of done, sub-tasks, and shutdown notes that preserve context between sessions.',
  },
  {
    icon: 'inbox',
    term: 'Capture',
    def: 'A quick note that lands in the Inbox (or a project) with a semantic tag — so jotting something down never derails what you were doing.',
  },
  {
    icon: 'bolt',
    term: 'Quick task',
    def: 'A 2–15 minute action parked on the Scratch Pad stack (max 5 active) — small enough to knock out between focus blocks.',
  },
  {
    icon: 'speed',
    term: 'WIP cap',
    def: 'At most 3 active projects. The cap is the feature: it forces a choice instead of letting everything be “in progress”.',
  },
];

// Copy-pasteable command chip — monospace, click-to-select.
function Cmd({ children }: { children: string }) {
  return (
    <code className="rounded bg-surface-2 border border-hairline px-1.5 py-0.5 font-mono text-[12px] text-ink select-all whitespace-nowrap">
      {children}
    </code>
  );
}

// One collapsible command row (native <details> — dependency-free, accessible).
function CommandRow({ entry }: { entry: CommandEntry }) {
  return (
    <details className="group panel">
      <summary className="flex items-center gap-2.5 px-3 py-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        <span className="material-icons text-base text-ink-4 transition-transform duration-150 group-open:rotate-90">
          chevron_right
        </span>
        <Cmd>{entry.cmd}</Cmd>
        <span className="text-sm text-ink-2 truncate">{entry.summary}</span>
      </summary>
      <div className="px-3 pb-3 pl-10 space-y-2 text-sm leading-relaxed text-ink-2">
        <p>{entry.what}</p>
        <div>
          <span className="eyebrow">Example</span>
          <div className="mt-1">
            <Cmd>{entry.example}</Cmd>
          </div>
        </div>
      </div>
    </details>
  );
}

export default function GuidePage() {
  return (
    <div className="max-w-3xl">
      <h1 className="title mb-2">Guide</h1>
      <p className="text-ink-3 mb-8">
        Squirrel keeps your projects, tasks, and working context in a plain-Markdown
        vault, and meets you on four surfaces: your coding agent (slash commands),
        the native desktop app with its menu-bar icon, this Web UI, and the{' '}
        <Cmd>squirrel</Cmd> CLI.
      </p>

      {/* ── Core concepts ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-3">Core concepts</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {CONCEPTS.map((c) => (
            <div key={c.term} className="panel p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="material-icons text-base text-accent">{c.icon}</span>
                <h3 className="font-medium text-ink">{c.term}</h3>
              </div>
              <p className="text-xs leading-relaxed text-ink-3">{c.def}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Configuration ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-3">Where the configuration lives</h2>
        <div className="panel p-4 text-sm leading-relaxed text-ink-2 space-y-2">
          <p>
            Everything Squirrel knows about your setup is in one file:{' '}
            <Cmd>~/.squirrel/config.toml</Cmd>. It registers your vaults — each
            with a <Cmd>name</Cmd>, a <Cmd>path</Cmd>, and a <Cmd>default</Cmd>{' '}
            flag — plus capture and notification preferences. Every surface (this
            Web UI, the desktop app, the CLI, your agent) reads the same file.
          </p>
          <p>
            If you move a vault folder, just update its <Cmd>path</Cmd> there (or
            run <Cmd>squirrel vaults</Cmd>) — the “Open Vault” buttons and all
            commands follow the configured path; nothing is hardcoded. The same{' '}
            <Cmd>~/.squirrel/</Cmd> directory also holds runtime files like logs
            and reminder state.
          </p>
        </div>
      </section>

      {/* ── A typical day ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-3">A typical day</h2>
        <ol className="space-y-3">
          {[
            ['/sq-start MYAPP', 'Open your agent and load yesterday’s context — what you were doing, the next physical action, and any blockers.'],
            ['/sq-capture …', 'Ideas and interruptions go straight to the vault, tagged and linked, so you can stay on the task at hand.'],
            ['/sq-focus today …', 'When everything feels urgent, pick one thing. The pick follows you to the desktop popup and this dashboard.'],
            ['/sq-end', 'Before you stop, write the shutdown note. Tomorrow’s /sq-start pays it back with interest.'],
          ].map(([cmd, text], i) => (
            <li key={cmd} className="panel p-4 flex items-start gap-3">
              <span className="chip chip-count shrink-0 mt-0.5">{i + 1}</span>
              <div className="min-w-0 text-sm text-ink-2 leading-relaxed">
                <Cmd>{cmd}</Cmd>
                <p className="mt-1">{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* ── Agent slash commands ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-1">In your coding agent</h2>
        <p className="text-sm text-ink-3 mb-4">
          Type these in Claude Code, Codex, Cursor, or Copilot (after{' '}
          <Cmd>squirrel install</Cmd>). Tap a command to see what it does.
        </p>
        <div className="space-y-6">
          {AGENT_GROUPS.map((g) => (
            <div key={g.title}>
              <h3 className="font-medium text-ink mb-0.5">{g.title}</h3>
              <p className="text-xs text-ink-4 mb-2">{g.blurb}</p>
              <div className="space-y-2">
                {g.entries.map((e) => (
                  <CommandRow key={e.cmd} entry={e} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Native desktop app ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-1">On your desktop — the popup</h2>
        <p className="text-sm text-ink-3 mb-4">
          The native app is a compact popup designed for glancing, not dwelling:
          see your focus, check in, capture, and get back to work.
        </p>
        <ul className="space-y-2 text-sm text-ink-2">
          {POPUP_FEATURES.map(([icon, term, def]) => (
            <li key={term} className="panel p-3 flex items-start gap-3">
              <span className="material-icons text-base text-accent mt-0.5">{icon}</span>
              <div className="min-w-0">
                <span className="font-medium text-ink">{term}</span>
                <span className="text-ink-3"> — {def}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* ── Menu-bar icon ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-1">On your desktop — the menu-bar icon</h2>
        <p className="text-sm text-ink-3 mb-4">
          The squirrel in your menu bar is more than a launcher: its dropdown
          updates with what needs attention right now.
        </p>
        <ul className="space-y-2 text-sm text-ink-2">
          {TRAY_FEATURES.map(([icon, term, def]) => (
            <li key={term} className="panel p-3 flex items-start gap-3">
              <span className="material-icons text-base text-accent mt-0.5">{icon}</span>
              <div className="min-w-0">
                <span className="font-medium text-ink">{term}</span>
                <span className="text-ink-3"> — {def}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* ── CLI ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-1">In the terminal</h2>
        <p className="text-sm text-ink-3 mb-4">
          The <Cmd>squirrel</Cmd> CLI reads the vault directly — no agent needed.
        </p>
        <div className="space-y-2">
          {CLI_COMMANDS.map((e) => (
            <CommandRow key={e.cmd} entry={e} />
          ))}
        </div>
      </section>

      {/* ── This Web UI ── */}
      <section className="mb-10">
        <h2 className="eyebrow text-ink-2 mb-1">In this Web UI</h2>
        <p className="text-sm text-ink-3 mb-4">
          Everything here reads and writes the same Markdown files your agent uses.
        </p>
        <ul className="space-y-2 text-sm text-ink-2">
          {[
            ['home', 'My projects', 'Your active projects as a list or board; open one to read and edit its tasks.'],
            ['event', 'Pressing', 'Deadlines grouped by urgency — the same data as /sq-deadlines.'],
            ['add', 'Add a note', 'The header button (and search with Cmd+K) captures a note without leaving the page.'],
            ['bolt', 'Quick Tasks', 'The lightning button parks 2–15 minute actions; knock them out between focus blocks.'],
            ['psychology', 'Mind Journal', 'The brain button is a recurring mood and “what’s on your mind” check-in; a dot appears when one is due.'],
            ['notifications', 'Notifications', 'Reminders and alerts fired by the background daemon land in the bell.'],
            ['settings', 'Settings', 'Vault switching, notification sounds, and other preferences.'],
          ].map(([icon, term, def]) => (
            <li key={term} className="panel p-3 flex items-start gap-3">
              <span className="material-icons text-base text-accent mt-0.5">{icon}</span>
              <div className="min-w-0">
                <span className="font-medium text-ink">{term}</span>
                <span className="text-ink-3"> — {def}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* ── FAQ ── */}
      <section className="mb-4">
        <h2 className="eyebrow text-ink-2 mb-3">FAQ</h2>
        <details className="group panel">
          <summary className="flex items-center gap-2.5 px-3 py-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
            <span className="material-icons text-base text-ink-4 transition-transform duration-150 group-open:rotate-90">
              chevron_right
            </span>
            <span className="text-sm text-ink-2">
              “Open Vault” shows an Obsidian error: <em>Vault not found</em>
            </span>
          </summary>
          <div className="px-3 pb-3 pl-10 space-y-2 text-sm leading-relaxed text-ink-2">
            <p>
              Obsidian can only open vaults it already knows about. If your vault
              folder was created by Squirrel (or has simply never been opened in
              Obsidian), it exists on disk but isn’t in Obsidian’s registry yet —
              so Obsidian replies “Vault not found”.
            </p>
            <p>
              To fix it once: open Obsidian → vault switcher →{' '}
              <strong>“Open folder as vault”</strong> → pick your vault folder
              (the <Cmd>path</Cmd> registered in{' '}
              <Cmd>~/.squirrel/config.toml</Cmd>). After that one-time
              registration, the “Open Vault” buttons open it directly.
            </p>
          </div>
        </details>
      </section>
    </div>
  );
}
