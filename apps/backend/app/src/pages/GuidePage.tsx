// Guide / tutorial page — how to use Squirrel across its three surfaces:
// your coding agent (slash commands), the `squirrel` CLI, and this Web UI.
// Static content; commands mirror agent-pack/commands/ and apps/cli/squirrel.
//
// A sticky search box filters every section live (commands, concepts,
// features, FAQ); quick-jump chips scroll to each section when not searching.

import { useState, type ReactNode } from 'react';

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

const WEBUI_FEATURES: [string, string, string][] = [
  ['home', 'My projects', 'Your active projects as a list or board; open one to read and edit its tasks.'],
  ['event', 'Pressing', 'Deadlines grouped by urgency — the same data as /sq-deadlines.'],
  ['add', 'Add a note', 'The header button (and search with Cmd+K) captures a note without leaving the page.'],
  ['bolt', 'Quick Tasks', 'The lightning button parks 2–15 minute actions; knock them out between focus blocks.'],
  ['psychology', 'Mind Journal', 'The brain button is a recurring mood and “what’s on your mind” check-in; a dot appears when one is due.'],
  ['notifications', 'Notifications', 'Reminders and alerts fired by the background daemon land in the bell.'],
  ['settings', 'Settings', 'Vault switching, notification sounds, and other preferences.'],
];

const DAY_STEPS: [string, string][] = [
  ['/sq-start MYAPP', 'Open your agent and load yesterday’s context — what you were doing, the next physical action, and any blockers.'],
  ['/sq-capture …', 'Ideas and interruptions go straight to the vault, tagged and linked, so you can stay on the task at hand.'],
  ['/sq-focus today …', 'When everything feels urgent, pick one thing. The pick follows you to the desktop popup and this dashboard.'],
  ['/sq-end', 'Before you stop, write the shutdown note. Tomorrow’s /sq-start pays it back with interest.'],
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

// ── Concept illustrations ────────────────────────────────────────────
// Two schematic diagrams rendered under the Core concepts grid: how the
// pieces nest inside the vault, and the lifecycle each piece moves through.
// Decorative JSX only — search matches via the haystacks below.

const CONCEPT_MAP_HAYSTACK =
  'how the pieces fit together diagram illustration vault folder anatomy active projects parking lot inbox scratch pad wip cap max 3 tasks inside projects captures land triage swap park free slot surfaces same files';

interface LifecycleStep {
  icon: string;
  label: string;
  sub: string;
  end?: boolean; // terminal state — rendered in the "ok" green
}

const LIFECYCLES: { icon: string; term: string; intro: string; steps: LifecycleStep[]; loop?: string }[] = [
  {
    icon: 'inbox',
    term: 'A capture',
    intro: 'From stray thought to real task — without derailing what you were doing.',
    steps: [
      { icon: 'edit', label: 'Jot it', sub: '/sq-capture, ⌘K, “Add a note”, or the popup' },
      { icon: 'inbox', label: 'Lands in the Inbox', sub: 'with a semantic tag, linked from its project page' },
      { icon: 'call_split', label: 'Triage it', sub: 'when you review — not when it interrupts you' },
      { icon: 'task_alt', label: 'Becomes a task', sub: 'in a project — or gets done, or dropped', end: true },
    ],
  },
  {
    icon: 'bolt',
    term: 'A quick task',
    intro: 'Too small for a project, too easy to forget.',
    steps: [
      { icon: 'bolt', label: 'Park it', sub: '⌃⌘Q anywhere, or the ⚡ button' },
      { icon: 'layers', label: 'Sits on the stack', sub: 'the Scratch Pad — max 5 active' },
      { icon: 'check_circle', label: 'Knock it out', sub: '2–15 minutes between focus blocks', end: true },
    ],
  },
  {
    icon: 'task_alt',
    term: 'A task (intent)',
    intro: 'The daily loop: each session ends on paper so the next one starts instantly.',
    steps: [
      { icon: 'play_arrow', label: '/sq-start', sub: 'loads the last shutdown note — state, next action, blockers' },
      { icon: 'center_focus_strong', label: 'Work', sub: 'check in to run a session timer that banks time into the task' },
      { icon: 'stop_circle', label: '/sq-end', sub: 'writes the shutdown note tomorrow-you will read' },
      { icon: 'flag', label: 'Done', sub: 'when its definition of done is met', end: true },
    ],
    loop: 'start → work → end repeats each session. Forgot /sq-end? /sq-recover reconstructs the context.',
  },
  {
    icon: 'rocket_launch',
    term: 'A project',
    intro: 'Held to at most 3 active at a time by the WIP cap.',
    steps: [
      { icon: 'add_circle', label: 'Created', sub: '/sq-new-project — refused if it would blow the WIP cap' },
      { icon: 'autorenew', label: 'Active', sub: 'one of ≤3 in 01-Active-Projects/' },
      { icon: 'pause_circle', label: 'Parked', sub: 'waits in the Parking Lot, off the cap' },
      { icon: 'inventory_2', label: 'Delivered', sub: '100% done — lands in the board’s DELIVERED lane', end: true },
    ],
    loop: 'Active ⇄ Parked is a swap, not a loss — park one to free a slot, reactivate it later.',
  },
];

const LIFECYCLE_HAYSTACK =
  'lifecycle life cycle journey flow diagram illustration steps stages ' +
  LIFECYCLES.map((l) => `${l.term} ${l.intro} ${l.steps.map((s) => `${s.label} ${s.sub}`).join(' ')} ${l.loop ?? ''}`)
    .join(' ')
    .toLowerCase();

// Mini folder box used inside the vault diagram (Inbox / Parking Lot / Scratch Pad).
function VaultBox({ icon, title, children }: { icon: string; title: string; children: ReactNode }) {
  return (
    <div className="rounded-md border border-hairline bg-paper p-2.5">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="material-icons text-sm text-accent">{icon}</span>
        <span className="text-[11px] font-semibold text-ink">{title}</span>
      </div>
      <p className="text-[11px] text-ink-4 leading-snug">{children}</p>
    </div>
  );
}

// Labeled connector between vault diagram rows (an interaction, not a folder).
function VaultArrow({ icon, children }: { icon: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-1.5 my-1.5 pl-3 text-[11px] text-ink-4">
      <span className="material-icons text-sm">{icon}</span>
      <span>{children}</span>
    </div>
  );
}

// Illustration 1 — the vault's anatomy: projects (under the WIP cap) hold
// tasks; captures land in the Inbox; quick tasks sit on the Scratch Pad
// outside any project.
function ConceptMapIllustration() {
  const miniTask = (id: string) => (
    <div className="flex items-center gap-1 rounded bg-surface-2 border border-hairline px-1.5 py-0.5">
      <span className="material-icons text-[12px] text-ink-4">task_alt</span>
      <span className="text-[10px] text-ink-3 truncate">{id} · task</span>
    </div>
  );
  return (
    <div className="panel p-4 overflow-x-auto">
      <div className="min-w-[540px]">
        <div className="rounded-lg border-2 border-dashed border-ink-4 bg-surface p-3">
          <div className="flex items-center gap-2 mb-3">
            <span className="material-icons text-base text-accent">folder</span>
            <span className="text-xs font-bold tracking-wide text-ink">VAULT</span>
            <span className="text-[11px] text-ink-4 truncate">
              one plain-Markdown folder — every box below is just .md files inside it
            </span>
          </div>

          {/* Active projects under the WIP cap */}
          <div className="rounded-md border border-hairline bg-paper p-2.5">
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-1.5">
                <span className="material-icons text-sm text-accent">rocket_launch</span>
                <span className="text-[11px] font-semibold text-ink">01-Active-Projects/</span>
              </div>
              <span className="chip">
                <span className="material-icons text-sm">speed</span>
                WIP cap · max 3
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded border border-hairline bg-surface p-2">
                <div className="text-[10px] font-mono text-ink-3 mb-1.5">MYAPP/MYAPP.md</div>
                <div className="space-y-1">
                  {miniTask('AUTH-001')}
                  {miniTask('API-002')}
                </div>
              </div>
              <div className="rounded border border-hairline bg-surface p-2">
                <div className="text-[10px] font-mono text-ink-3 mb-1.5">FOO/FOO.md</div>
                {miniTask('FOO-001')}
              </div>
              <div className="rounded border border-dashed border-hairline p-2 flex items-center justify-center">
                <span className="text-[10px] text-ink-4 text-center leading-snug">
                  free slot — the cap forces a choice
                </span>
              </div>
            </div>
          </div>

          <VaultArrow icon="swap_vert">
            <strong className="text-ink-3">swap</strong> — park an active project or activate a parked
            one; the WIP cap guards this door
          </VaultArrow>

          <VaultBox icon="pause_circle" title="02-Parking-Lot/">
            paused projects wait here, off the cap — nothing is lost, it just isn’t “in progress”
          </VaultBox>

          <VaultArrow icon="north">
            <strong className="text-ink-3">triage</strong> — an Inbox capture graduates into a task
            inside a project
          </VaultArrow>

          <div className="grid grid-cols-2 gap-2">
            <VaultBox icon="inbox" title="Inbox">
              captures land here with a semantic tag — in via <strong className="text-ink-3">/sq-capture</strong>,
              “Add a note”, ⌘K, or the popup
            </VaultBox>
            <VaultBox icon="bolt" title="Scratch Pad">
              quick tasks (max 5) — 2–15 min actions that belong to no project; in via ⌃⌘Q or the ⚡ button
            </VaultBox>
          </div>
        </div>

        <p className="mt-2 text-[11px] text-ink-4 flex items-center gap-1.5">
          <span className="material-icons text-sm">sync_alt</span>
          Every surface — your agent, the CLI, the desktop popup, this Web UI — reads and writes these
          same files. There is no separate database.
        </p>
      </div>
    </div>
  );
}

// Illustration 2 — the lifecycle each piece moves through, as arrowed steppers.
function LifecycleIllustration() {
  return (
    <div className="space-y-3">
      {LIFECYCLES.map((lc) => (
        <div key={lc.term} className="panel p-4">
          <div className="flex items-baseline gap-2 mb-3 flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="material-icons text-base text-accent self-center">{lc.icon}</span>
              <span className="text-sm font-medium text-ink">{lc.term}</span>
            </div>
            <span className="text-xs text-ink-4">{lc.intro}</span>
          </div>
          <div className="flex flex-wrap items-stretch gap-y-2">
            {lc.steps.map((s, i) => (
              // Arrow + box form one flex item so a line-wrap never strands an arrow.
              <div key={s.label} className="flex items-stretch">
                {i > 0 && (
                  <span className="material-icons self-center text-base text-ink-4 mx-1.5" aria-hidden>
                    east
                  </span>
                )}
                <div className="rounded-md border border-hairline bg-surface px-2.5 py-1.5 max-w-[190px]">
                  <div className="flex items-center gap-1.5">
                    <span className={`material-icons text-[14px] ${s.end ? 'text-ok' : 'text-ink-3'}`}>
                      {s.icon}
                    </span>
                    <span className={`text-xs font-semibold whitespace-nowrap ${s.end ? 'text-ok' : 'text-ink'}`}>
                      {s.label}
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-4 leading-snug mt-0.5">{s.sub}</p>
                </div>
              </div>
            ))}
          </div>
          {lc.loop && (
            <div className="mt-2.5 flex items-center gap-1.5 text-[11px] text-ink-4">
              <span className="material-icons text-[14px]">replay</span>
              <span>{lc.loop}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Searchable text for the configuration panel (rendered as prose below).
const CONFIG_HAYSTACK =
  'where the configuration lives ~/.squirrel/config.toml vaults name path default flag capture notification preferences move vault folder squirrel vaults open vault buttons logs reminder state';

// Board lane reference — mirrors BOARD_HELP_ROWS in HomePage's BoardView.
const BOARD_COLUMNS: { dot: string; label: string; rule: string }[] = [
  {
    dot: 'bg-critical',
    label: 'PRESSING',
    rule: 'Needs attention now — a computed feed of your most urgent items (top 3): overdue, due today, or due tomorrow. It can hold tasks and notes, not just projects. Always first so it stays the focus; you can’t drop cards here, but you can drag one into a lane to defer it.',
  },
  {
    dot: 'bg-hairline',
    label: 'LATER',
    rule: 'Deadline more than 30 days away — early stage. Drop a card here to push its deadline out to roughly two months from today.',
  },
  {
    dot: 'bg-accent',
    label: 'ACTIVE',
    rule: 'Deadline within 8–30 days, or no deadline set — your default working lane. Drop a card here to set its deadline about three weeks out.',
  },
  {
    dot: 'bg-warning',
    label: 'THIS WEEK',
    rule: 'Deadline within 7 days — about to close. Drop a card here to commit to finishing it within the next few days.',
  },
  {
    dot: 'bg-ok',
    label: 'DELIVERED',
    rule: '100% complete or marked delivered — done. Drop a project card here to mark it delivered without opening it.',
  },
];

// Searchable text for the dashboard section (board + list views).
const DASHBOARD_HAYSTACK =
  'dashboard board list view toggle columns lanes kanban how the columns work pressing later active this week delivered drag drop card deadline defer move project urgency left right done ' +
  BOARD_COLUMNS.map((c) => `${c.label} ${c.rule}`).join(' ').toLowerCase();

interface FaqEntry {
  q: string;
  haystack: string; // q + answer text, for search
  body: ReactNode;
}

const FAQ_ENTRIES: FaqEntry[] = [
  {
    q: 'How do I install Squirrel?',
    haystack:
      'how do i install squirrel download dmg pkg installer applications double-click setup get started',
    body: (
      <>
        <p>
          Download <Cmd>squirrel-macos.dmg</Cmd>, open it, and double-click the{' '}
          <Cmd>.pkg</Cmd> inside. The guided installer puts <strong>Squirrel.app</strong>{' '}
          in <Cmd>/Applications</Cmd>, the <Cmd>squirrel</Cmd> CLI in{' '}
          <Cmd>/usr/local/bin</Cmd>, wires the slash commands into any coding
          agents you have installed, and seeds a starter config and vault. No
          Terminal needed.
        </p>
        <p>
          When it finishes, launch it with <Cmd>⌘ Space</Cmd> → “Squirrel” — the
          squirrel icon appears in your menu bar.
        </p>
      </>
    ),
  },
  {
    q: 'macOS says the app “can’t be opened” (unidentified developer)',
    haystack:
      'macos gatekeeper cant be opened unidentified developer damaged security warning right-click open unsigned',
    body: (
      <p>
        Squirrel is currently unsigned, so Gatekeeper blocks a normal
        double-click the first time. Right-click (or Ctrl-click){' '}
        <strong>Squirrel.app</strong> → <strong>Open</strong> → confirm. You only
        need to do this once — afterwards it opens normally.
      </p>
    ),
  },
  {
    q: 'Do I need Claude Code (or another coding agent) to use Squirrel?',
    haystack:
      'do i need claude code codex cursor copilot windsurf coding agent required optional slash commands prerequisites',
    body: (
      <>
        <p>
          No. The desktop popup, the menu-bar icon, this Web UI, and the{' '}
          <Cmd>squirrel</Cmd> CLI all work on their own — capture notes, manage
          quick tasks, track deadlines, run focus sessions.
        </p>
        <p>
          A coding agent (Claude Code, Codex, Cursor, Copilot, Windsurf) adds the{' '}
          <Cmd>/sq-*</Cmd> slash commands for richer workflows like{' '}
          <Cmd>/sq-start</Cmd> and <Cmd>/sq-brief</Cmd>. If you install an agent
          later, run <Cmd>squirrel install --agent claude</Cmd> (auto-detects
          others) to wire it up.
        </p>
      </>
    ),
  },
  {
    q: 'My company blocks installing plugins — can I still use the /sq-* commands?',
    haystack:
      'company corporate org blocks plugins marketplace restricted locked down enterprise managed policy no-plugin manual install claude code skills commands hooks settings.json ~/.claude/skills ~/.claude/commands disableallhooks install-claude-manual',
    body: (
      <>
        <p>
          Yes. Some organizations block Claude Code’s plugin marketplace, so the
          normal <Cmd>squirrel install --agent claude</Cmd> (which registers a
          plugin) won’t load. Use the <strong>no-plugin installer</strong>{' '}
          instead — it drops the skills and <Cmd>/sq-*</Cmd> commands into Claude
          Code’s native personal folders, which load without the marketplace and
          aren’t affected by the plugin block:
        </p>
        <p>
          <Cmd>./scripts/install-claude.sh --no-plugin</Cmd> (or run{' '}
          <Cmd>./scripts/install-claude-manual.sh</Cmd> directly).
        </p>
        <p>
          It installs the skills to <Cmd>~/.claude/skills/</Cmd>, the commands to{' '}
          <Cmd>~/.claude/commands/</Cmd>, and merges the hooks into{' '}
          <Cmd>~/.claude/settings.json</Cmd> — nothing under{' '}
          <Cmd>~/.claude/plugins/</Cmd>. Restart Claude Code and the{' '}
          <Cmd>/sq-*</Cmd> commands appear as usual (there’s no{' '}
          <Cmd>/plugin list</Cmd> entry — that’s expected).
        </p>
        <p>
          One caveat: if your org also sets <Cmd>"disableAllHooks": true</Cmd> in
          managed settings, the proactive hook nudges won’t fire — but the skills
          and slash commands still work. Undo it any time with{' '}
          <Cmd>./scripts/uninstall-claude-manual.sh</Cmd>.
        </p>
      </>
    ),
  },
  {
    q: 'Do I need Obsidian?',
    haystack: 'do i need obsidian required optional markdown editor view vault',
    body: (
      <p>
        No. Your vault is plain Markdown — readable and editable with anything.
        Obsidian is just a nice way to browse it (the vault format is
        Obsidian-compatible, and the “Open Vault” buttons deep-link into it if
        you use it), but nothing in Squirrel depends on it.
      </p>
    ),
  },
  {
    q: 'I already have an Obsidian vault — how do I bring it in?',
    haystack:
      'existing obsidian vault import migrate bring notes sq-migrate-vault dry-run add vault register',
    body: (
      <>
        <p>
          Run <Cmd>/sq-migrate-vault ~/path/to/your-old-vault</Cmd> in your
          coding agent. It scans the old vault, maps folders to projects and
          notes to tasks, shows you a dry-run plan first, and{' '}
          <strong>never modifies the original vault</strong>.
        </p>
        <p>
          If you just want Squirrel to use a folder as-is, register it instead:{' '}
          <Cmd>squirrel vaults add work ~/path/to/vault</Cmd>.
        </p>
      </>
    ),
  },
  {
    q: 'Where is my data? Does anything leave my machine?',
    haystack:
      'where is my data privacy local cloud sync telemetry security markdown files own your data offline',
    body: (
      <>
        <p>
          Everything is local. Your notes live as plain <Cmd>.md</Cmd> files in
          your vault folder; settings and logs live in <Cmd>~/.squirrel/</Cmd>.
          The backend serves this Web UI on <Cmd>127.0.0.1</Cmd> only — it is
          not reachable from the network, and nothing is synced to a cloud or
          phoned home.
        </p>
        <p>
          That also means backups are your call: the vault is a normal folder,
          so anything that backs up folders (Time Machine, git, iCloud Drive)
          works.
        </p>
      </>
    ),
  },
  {
    q: 'How do I open this Web UI again later?',
    haystack:
      'open web ui again url browser localhost 3939 squirrel web open tray menu dashboard',
    body: (
      <p>
        Three ways: click <strong>Open Web UI</strong> in the menu-bar dropdown,
        click the same button in the desktop popup’s footer, or run{' '}
        <Cmd>squirrel web open</Cmd> in a terminal (it starts the server first
        if needed).
      </p>
    ),
  },
  {
    q: 'How do I update Squirrel?',
    haystack:
      'update upgrade new version installer latest release config preserved install log before after snapshot backend offline recovery',
    body: (
      <>
        <p>
          Download the newer DMG and run the installer again. It detects your
          existing version, swaps the binaries, and replaces the agent commands —
          your <Cmd>~/.squirrel/config.toml</Cmd> and your vault are never
          touched.
        </p>
        <p>
          Each run records a before/after snapshot of the install under{' '}
          <Cmd>~/.squirrel/install-logs/</Cmd>, so if an upgrade ever leaves the
          app stuck on “Backend offline,” that log shows what changed. The usual
          culprit is a leftover background service from an older install —
          reinstalling with the <Cmd>.pkg</Cmd> installer retires it
          automatically.
        </p>
      </>
    ),
  },
  {
    q: 'How do I uninstall?',
    haystack:
      'uninstall remove delete squirrel app cli config vault kept trash applications dry-run preview confirm admin password sudo',
    body: (
      <>
        <p>
          Run the bundled <Cmd>uninstall.sh</Cmd> — it removes the app, CLI,
          background service, agent commands, and app data in one pass. For a{' '}
          <Cmd>.pkg</Cmd> install run{' '}
          <Cmd>/usr/local/share/squirrel/uninstall.sh</Cmd>; for a DMG or
          manual-zip install run <Cmd>./uninstall.sh</Cmd> from the mounted DMG
          or unzipped folder.
        </p>
        <p>
          It prints exactly what it will remove and asks you to confirm first —
          add <Cmd>--dry-run</Cmd> to preview without touching anything, or{' '}
          <Cmd>--yes</Cmd> to skip the prompt. Only system files under{' '}
          <Cmd>/usr/local</Cmd> ask for your admin password; if you only ever ran
          the drag-installer, it won’t ask at all.
        </p>
        <p>
          <strong>Your vaults are never deleted.</strong> The uninstaller reads
          every vault path from your config first and leaves those folders of
          Markdown files exactly where they are.
        </p>
      </>
    ),
  },
  {
    q: 'Where can I find install diagnostics for troubleshooting?',
    haystack:
      'install log logs diagnostics troubleshoot what changed before after snapshot install-logs failed install upgrade support metadata no secrets safe to share',
    body: (
      <>
        <p>
          Every installer run writes a timestamped before/after snapshot to{' '}
          <Cmd>~/.squirrel/install-logs/</Cmd>. Each one captures which Squirrel
          files and background services were on the system before the install and
          after — so when something looks wrong, the diff between the two sections
          points straight at what changed.
        </p>
        <p>
          The log records file metadata only — sizes, timestamps, and checksums,
          never your notes or any tokens — so it’s safe to share when you ask for
          help. The newest ten runs are kept; older logs are pruned automatically.
        </p>
      </>
    ),
  },
  {
    q: 'The popup says “Backend offline” — what do I do?',
    haystack:
      'backend offline unavailable not responding error red banner restart service logs squirrel.log install-logs troubleshoot upgrade port collision leftover service',
    body: (
      <>
        <p>
          First try <strong>Restart Service</strong> in the menu-bar dropdown —
          it relaunches the bundled backend. If it keeps happening, check the
          log at <Cmd>~/.squirrel/squirrel.log</Cmd> for the reason.
        </p>
        <p>
          A common cause is two Squirrels fighting over the same port (for
          example, the installed app plus a development copy). Quit one of them
          and restart the other.
        </p>
        <p>
          If it started right after an update, the before/after snapshots in{' '}
          <Cmd>~/.squirrel/install-logs/</Cmd> show what the install changed —
          usually a leftover background service from an older copy. Reinstalling
          with the <Cmd>.pkg</Cmd> installer retires it and clears the conflict.
        </p>
      </>
    ),
  },
  {
    q: 'I clicked a notification and nothing happened',
    haystack:
      'notification banner click nothing happened macos not clickable menu bar icon act reminders',
    body: (
      <p>
        That’s a macOS limitation — Squirrel’s notification banners aren’t
        clickable. The menu-bar squirrel is where you act on them: reminders,
        pressing items, and check-ins all appear in its dropdown, and the bell
        in the popup and this Web UI collects them too.
      </p>
    ),
  },
  {
    q: 'What does “Pressing” mean, and how does something get there?',
    haystack:
      'pressing what is it deadline urgency overdue critical urgent due today tomorrow how add deadline appears tray popup',
    body: (
      <>
        <p>
          “Pressing” is everything with a deadline that needs attention{' '}
          <em>now</em>: items that are <strong>overdue</strong>, due{' '}
          <strong>today</strong>, or due <strong>tomorrow</strong>. Anything
          further out stays in the calmer urgency bands (soon, upcoming,
          eventual) and only shows on the Pressing page and{' '}
          <Cmd>/sq-deadlines</Cmd> report — not in your face.
        </p>
        <p>
          An item becomes pressing automatically when its <Cmd>deadline</Cmd>{' '}
          gets close — give a task or note a deadline (e.g.{' '}
          <Cmd>/sq-capture pay the visa bill before June 30</Cmd>) and Squirrel
          tracks it from there. Pressing items surface everywhere: the PRESSING
          section of the desktop popup, “PRESSING NOW” in the menu-bar dropdown,
          and the Pressing page in this Web UI.
        </p>
      </>
    ),
  },
  {
    q: 'What’s the difference between the Board and List views?',
    haystack:
      'board list view difference toggle switch header dashboard kanban columns lanes which view projects pressing',
    body: (
      <>
        <p>
          They’re two readings of the same data. <strong>Board</strong> lays your
          projects out as a pipeline — five columns flowing left → right toward
          done — so you see at a glance what’s early, what’s closing, and what’s
          finished. <strong>List</strong> is a calmer vertical read: pressing
          items on top, then every project with its deadline, progress, and last
          activity.
        </p>
        <p>
          Switch between them with the <strong>List / Board</strong> toggle in
          the header. Use Board when you’re planning the week and want to move
          things; use List when you just want to scan.
        </p>
      </>
    ),
  },
  {
    q: 'What actually happens when I drag a card between board columns?',
    haystack:
      'drag drop card board column lane move deadline rewrite change confirm dialog this week active later delivered defer',
    body: (
      <>
        <p>
          The columns are computed from each project’s <Cmd>deadline</Cmd>, so
          moving a card <em>rewrites its deadline</em> (after a confirmation
          dialog — nothing changes silently). Dropping into{' '}
          <strong>THIS WEEK</strong> sets the deadline a few days out,{' '}
          <strong>ACTIVE</strong> about three weeks out, <strong>LATER</strong>{' '}
          about two months out, and <strong>DELIVERED</strong> marks the project
          delivered.
        </p>
        <p>
          The change is written to the project’s Markdown frontmatter in your
          vault — so the new deadline is immediately visible to{' '}
          <Cmd>/sq-deadlines</Cmd>, the desktop popup, and every other surface.
        </p>
      </>
    ),
  },
  {
    q: 'Why can’t I drop a card into PRESSING — and how do I get one out?',
    haystack:
      'pressing column drop not allowed cant move computed automatic top 3 defer drag out remove mark done finish',
    body: (
      <>
        <p>
          PRESSING isn’t a real lane — it’s a computed feed of your three most
          urgent items (overdue, due today, or due tomorrow). Items enter it
          automatically when their deadline gets close, so you can’t place cards
          there by hand.
        </p>
        <p>
          To get something <em>out</em>, you have two options: drag it into a
          deadline lane (THIS WEEK / ACTIVE / LATER) to <strong>defer</strong> it
          — its deadline is pushed out and it leaves the feed — or open the item
          and mark it done. Dragging a pressing card straight to DELIVERED is
          intentionally blocked, so “done” stays a deliberate act, not a slip of
          the mouse.
        </p>
      </>
    ),
  },
  {
    q: 'Why did my project move to a different column by itself?',
    haystack:
      'project moved column by itself automatically changed lane jumped this week active later no deadline time passing',
    body: (
      <p>
        Because the lanes are time-based, cards migrate on their own as
        deadlines approach: a project in LATER drifts into ACTIVE once its
        deadline is within 30 days, then into THIS WEEK inside 7 days — no
        action needed. A project with <em>no</em> deadline always sits in
        ACTIVE, the default working lane. The board is recomputed every time
        you look at it, so it always reflects today.
      </p>
    ),
  },
  {
    q: 'Why can I only have 3 active projects?',
    haystack:
      'why only 3 active projects wip cap limit work in progress parking lot increase more projects',
    body: (
      <p>
        The WIP cap is deliberate — it’s the core of Squirrel’s philosophy.
        Letting everything be “in progress” is how projects stall; the cap
        forces a real choice about what matters now. Extra projects aren’t
        lost: park them in the Parking Lot and swap one in when you finish (or
        consciously pause) an active one.
      </p>
    ),
  },
  {
    q: '“Open Vault” shows an Obsidian error: Vault not found',
    haystack:
      'open vault obsidian error vault not found registry open folder as vault config.toml path one-time registration',
    body: (
      <>
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
      </>
    ),
  },
];

// Quick-jump targets — order matches the sections below.
const NAV: [string, string][] = [
  ['concepts', 'Concepts'],
  ['configuration', 'Configuration'],
  ['typical-day', 'A typical day'],
  ['agent', 'Agent commands'],
  ['popup', 'Desktop popup'],
  ['menu-bar', 'Menu bar'],
  ['cli', 'CLI'],
  ['web-ui', 'Web UI'],
  ['dashboard', 'Dashboard'],
  ['faq', 'FAQ'],
];

// Editorial section header: mono kicker (step number + section name) +
// a Fraunces serif title + an optional one-line subtitle. Restores a real
// type scale on top of the old 9.5px eyebrow headings.
function SectionHeader({ id, title, children }: { id: string; title: string; children?: ReactNode }) {
  const idx = NAV.findIndex(([nid]) => nid === id);
  const num = String(idx + 1).padStart(2, '0');
  const label = (NAV[idx]?.[1] ?? '').toUpperCase();
  return (
    <header className="mb-6">
      <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-accent mb-2">
        Section {num} · {label}
      </p>
      <h2 className="font-serif text-[27px] sm:text-[31px] leading-[1.1] tracking-[-0.01em] text-ink">
        {title}
      </h2>
      {children && (
        <p className="mt-2.5 text-[15px] leading-relaxed text-ink-3 max-w-2xl">{children}</p>
      )}
    </header>
  );
}

// Sub-section heading inside a section — a real sans heading, clearly above
// body text but below the serif section title.
function SubHeader({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-base font-bold tracking-tight text-ink mb-2.5 mt-9 first:mt-0">
      {children}
    </h3>
  );
}

// Prev / Next pager — turns the one-section-at-a-time docs view into a guided
// path so "what's next" is always one click away.
function SectionPager({ active, onNavigate }: { active: string; onNavigate: (id: string) => void }) {
  const idx = NAV.findIndex(([id]) => id === active);
  const prev = idx > 0 ? NAV[idx - 1] : null;
  const next = idx < NAV.length - 1 ? NAV[idx + 1] : null;
  return (
    <nav
      aria-label="Guide pagination"
      className="mt-12 pt-6 border-t border-hairline flex items-center justify-between gap-3"
    >
      {prev ? (
        <button
          type="button"
          onClick={() => onNavigate(prev[0])}
          className="group flex items-center gap-3 text-left rounded-lg px-3 py-2 -ml-3 hover:bg-surface-2 transition-colors"
        >
          <span className="material-icons text-ink-4 group-hover:text-accent transition-colors">arrow_back</span>
          <span className="min-w-0">
            <span className="block font-mono text-[9.5px] font-semibold uppercase tracking-[0.16em] text-ink-4">Previous</span>
            <span className="block text-sm font-semibold text-ink-2 group-hover:text-accent transition-colors truncate">{prev[1]}</span>
          </span>
        </button>
      ) : (
        <span />
      )}
      {next ? (
        <button
          type="button"
          onClick={() => onNavigate(next[0])}
          className="group flex items-center gap-3 text-right rounded-lg px-3 py-2 -mr-3 hover:bg-surface-2 transition-colors"
        >
          <span className="min-w-0">
            <span className="block font-mono text-[9.5px] font-semibold uppercase tracking-[0.16em] text-ink-4">Next</span>
            <span className="block text-sm font-semibold text-ink-2 group-hover:text-accent transition-colors truncate">{next[1]}</span>
          </span>
          <span className="material-icons text-ink-4 group-hover:text-accent transition-colors">arrow_forward</span>
        </button>
      ) : (
        <span />
      )}
    </nav>
  );
}

// Copy-pasteable command chip — monospace, click-to-select.
function Cmd({ children }: { children: string }) {
  return (
    <code className="rounded bg-surface-2 border border-hairline px-1.5 py-0.5 font-mono text-[12px] text-ink select-all whitespace-nowrap">
      {children}
    </code>
  );
}

// One collapsible command row (native <details> — dependency-free, accessible).
// `forceOpen` expands the row while a search is active so matches are readable.
function CommandRow({ entry, forceOpen }: { entry: CommandEntry; forceOpen?: boolean }) {
  return (
    <details className="group panel" open={forceOpen || undefined}>
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

// Icon + term + definition list shared by the popup / menu-bar / Web UI sections.
function FeatureList({ features }: { features: [string, string, string][] }) {
  return (
    <ul className="space-y-2 text-sm text-ink-2">
      {features.map(([icon, term, def]) => (
        <li key={term} className="panel p-3 flex items-start gap-3">
          <span className="material-icons text-base text-accent mt-0.5">{icon}</span>
          <div className="min-w-0">
            <span className="font-medium text-ink">{term}</span>
            <span className="text-ink-3"> — {def}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function GuidePage() {
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const searching = q.length > 0;
  const hit = (...fields: string[]) =>
    !searching || fields.some((f) => f.toLowerCase().includes(q));

  // Filtered views of every section's data.
  const concepts = CONCEPTS.filter((c) => hit(c.term, c.def));
  const showConceptMap = hit(CONCEPT_MAP_HAYSTACK);
  const showLifecycles = hit(LIFECYCLE_HAYSTACK);
  const showConfig = hit(CONFIG_HAYSTACK);
  const daySteps = DAY_STEPS.filter(([cmd, text]) => hit(cmd, text));
  const agentGroups = AGENT_GROUPS.map((g) => ({
    ...g,
    entries: g.entries.filter((e) => hit(e.cmd, e.summary, e.what, e.example, g.title)),
  })).filter((g) => g.entries.length > 0);
  const cliCommands = CLI_COMMANDS.filter((e) => hit(e.cmd, e.summary, e.what, e.example));
  const popupFeatures = POPUP_FEATURES.filter(([, term, def]) => hit(term, def));
  const trayFeatures = TRAY_FEATURES.filter(([, term, def]) => hit(term, def));
  const webuiFeatures = WEBUI_FEATURES.filter(([, term, def]) => hit(term, def));
  const showDashboard = hit(DASHBOARD_HAYSTACK);
  const faqEntries = FAQ_ENTRIES.filter((f) => hit(f.haystack));

  const matchCount =
    concepts.length +
    (showConceptMap ? 1 : 0) +
    (showLifecycles ? 1 : 0) +
    (showConfig ? 1 : 0) +
    (showDashboard ? 1 : 0) +
    daySteps.length +
    agentGroups.reduce((n, g) => n + g.entries.length, 0) +
    cliCommands.length +
    popupFeatures.length +
    trayFeatures.length +
    webuiFeatures.length +
    faqEntries.length;

  // Docs-style navigation: the sub-sidebar shows one section at a time; an
  // active search overrides the selection and sweeps every section.
  const [active, setActive] = useState<string>(NAV[0][0]);
  const show = (id: string, hasMatch: boolean) => (searching ? hasMatch : active === id);

  const selectSection = (id: string) => {
    setActive(id);
    setQuery('');
    document.querySelector('main')?.scrollTo({ top: 0 });
  };

  return (
    <div className="max-w-5xl">
      <header className="mb-8">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-accent mb-2.5">
          Squirrel · Guide
        </p>
        <h1 className="font-serif text-[40px] sm:text-[46px] leading-[1.04] tracking-[-0.015em] text-ink mb-3.5">
          Guide
        </h1>
        <p className="text-[15px] leading-relaxed text-ink-3 max-w-3xl">
          Squirrel keeps your projects, tasks, and working context in a plain-Markdown
          vault, and meets you on four surfaces: your coding agent (slash commands),
          the native desktop app with its menu-bar icon, this Web UI, and the{' '}
          <Cmd>squirrel</Cmd> CLI.
        </p>
      </header>

      <div className="flex flex-col md:flex-row md:items-start gap-6">
        {/* ── Sub-sidebar (horizontal chips on small screens) ── */}
        <aside className="md:w-52 md:shrink-0 md:sticky md:top-0">
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-ink-3 mb-3 px-2 hidden md:block">
            Guide · {Math.max(1, NAV.findIndex(([id]) => id === active) + 1)} / {NAV.length}
          </p>
          <nav aria-label="Guide sections" className="flex flex-row flex-wrap md:flex-col gap-1">
            {NAV.map(([id, label], i) => {
              const isActive = !searching && active === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => selectSection(id)}
                  aria-current={isActive ? 'true' : undefined}
                  className={`group relative flex items-center gap-3 text-left rounded-md pl-3 pr-3 py-2 text-sm transition-colors ${
                    isActive
                      ? 'bg-focus-tint text-accent font-semibold'
                      : 'text-ink-2 hover:bg-surface-2'
                  }`}
                >
                  {isActive && (
                    <span
                      className="hidden md:block absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-accent"
                      aria-hidden
                    />
                  )}
                  <span
                    className={`font-mono text-[11px] tabular-nums ${
                      isActive ? 'text-accent' : 'text-ink-4 group-hover:text-ink-3'
                    }`}
                    aria-hidden
                  >
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span>{label}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* ── Content column ── */}
        <div className="flex-1 min-w-0 max-w-3xl">

      {/* ── Search the guide (pinned below the app header) ── */}
      <div className="sticky top-0 z-10 -mx-3 px-3 pt-3 pb-5 mb-8 bg-bg border-b border-hairline shadow-[0_16px_28px_-10px_rgba(14,17,22,0.45)]">
        <div className="relative group">
          <span className="material-icons absolute left-3.5 top-1/2 -translate-y-1/2 text-lg text-ink-4 pointer-events-none group-focus-within:text-accent transition-colors">
            search
          </span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setQuery('');
            }}
            placeholder="Search the guide — commands, concepts, FAQ…"
            aria-label="Search the guide"
            className="w-full pl-11 pr-10 py-2.5 text-sm border border-hairline rounded-lg bg-surface text-ink shadow-[0_2px_4px_rgba(14,17,22,0.06),0_14px_30px_-8px_rgba(14,17,22,0.32)] focus:border-accent focus:ring-0 outline-none transition-all placeholder-ink-4 [&::-webkit-search-cancel-button]:hidden"
          />
          {searching && (
            <button
              type="button"
              onClick={() => setQuery('')}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-md text-ink-4 hover:text-ink hover:bg-surface-2"
            >
              <span className="material-icons text-base">close</span>
            </button>
          )}
        </div>
        {searching && (
          <p className="mt-2 px-1 text-xs text-ink-3">
            {matchCount === 0
              ? 'No matches'
              : `${matchCount} ${matchCount === 1 ? 'match' : 'matches'}`}{' '}
            for “{query.trim()}” — across every section
          </p>
        )}
      </div>

      {/* ── Empty state ── */}
      {searching && matchCount === 0 && (
        <div className="panel p-8 text-center">
          <span className="material-icons text-3xl text-ink-4">search_off</span>
          <p className="mt-2 text-sm text-ink-2">
            Nothing in the guide matches “{query.trim()}”.
          </p>
          <button type="button" onClick={() => setQuery('')} className="btn mt-4">
            Clear search
          </button>
        </div>
      )}

      {/* ── Core concepts ── */}
      {show('concepts', concepts.length > 0 || showConceptMap || showLifecycles) && (
        <section id="guide-concepts" className="mb-10 scroll-mt-24">
          <SectionHeader id="concepts" title="The pieces Squirrel is made of">
            A handful of nouns — learn these and the rest of the guide reads itself.
          </SectionHeader>
          {concepts.length > 0 && (
            <>
              <SubHeader>Core concepts</SubHeader>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {concepts.map((c) => (
                  <div key={c.term} className="panel p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="material-icons text-base text-accent">{c.icon}</span>
                      <h3 className="font-medium text-ink">{c.term}</h3>
                    </div>
                    <p className="text-xs leading-relaxed text-ink-3">{c.def}</p>
                  </div>
                ))}
              </div>
            </>
          )}

          {showConceptMap && (
            <>
              <SubHeader>How the pieces fit together</SubHeader>
              <p className="text-sm text-ink-3 mb-3">
                Everything above is just files nested inside one folder — projects hold tasks,
                captures land in the Inbox, quick tasks sit on the Scratch Pad, and the WIP cap
                guards the active shelf.
              </p>
              <ConceptMapIllustration />
            </>
          )}

          {showLifecycles && (
            <>
              <SubHeader>The life of each piece</SubHeader>
              <p className="text-sm text-ink-3 mb-3">
                Each piece moves through a small, predictable loop — green marks where it comes
                to rest.
              </p>
              <LifecycleIllustration />
            </>
          )}
        </section>
      )}

      {/* ── Configuration ── */}
      {show('configuration', showConfig) && (
        <section id="guide-configuration" className="mb-10 scroll-mt-24">
          <SectionHeader id="configuration" title="Where the configuration lives">
            One file describes your whole setup — and every surface reads it.
          </SectionHeader>
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
      )}

      {/* ── A typical day ── */}
      {show('typical-day', daySteps.length > 0) && (
        <section id="guide-typical-day" className="mb-10 scroll-mt-24">
          <SectionHeader id="typical-day" title="A typical day">
            The loop, end to end — from opening your work to shutting it down.
          </SectionHeader>
          <ol className="space-y-3">
            {daySteps.map(([cmd, text]) => (
              <li key={cmd} className="panel p-4 flex items-start gap-3">
                <span className="chip chip-count shrink-0 mt-0.5">
                  {DAY_STEPS.findIndex(([c]) => c === cmd) + 1}
                </span>
                <div className="min-w-0 text-sm text-ink-2 leading-relaxed">
                  <Cmd>{cmd}</Cmd>
                  <p className="mt-1">{text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* ── Agent slash commands ── */}
      {show('agent', agentGroups.length > 0) && (
        <section id="guide-agent" className="mb-10 scroll-mt-24">
          <SectionHeader id="agent" title="In your coding agent">
            Type these in Claude Code, Codex, Cursor, or Copilot (after{' '}
            <Cmd>squirrel install</Cmd>). Tap a command to see what it does.
          </SectionHeader>
          <div className="space-y-6">
            {agentGroups.map((g) => (
              <div key={g.title}>
                <h3 className="font-medium text-ink mb-0.5">{g.title}</h3>
                <p className="text-xs text-ink-4 mb-2">{g.blurb}</p>
                <div className="space-y-2">
                  {g.entries.map((e) => (
                    <CommandRow key={e.cmd} entry={e} forceOpen={searching} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Native desktop app ── */}
      {show('popup', popupFeatures.length > 0) && (
        <section id="guide-popup" className="mb-10 scroll-mt-24">
          <SectionHeader id="popup" title="On your desktop — the popup">
            The native app is a compact popup designed for glancing, not dwelling:
            see your focus, check in, capture, and get back to work.
          </SectionHeader>
          <FeatureList features={popupFeatures} />
        </section>
      )}

      {/* ── Menu-bar icon ── */}
      {show('menu-bar', trayFeatures.length > 0) && (
        <section id="guide-menu-bar" className="mb-10 scroll-mt-24">
          <SectionHeader id="menu-bar" title="On your desktop — the menu-bar icon">
            The squirrel in your menu bar is more than a launcher: its dropdown
            updates with what needs attention right now.
          </SectionHeader>
          <FeatureList features={trayFeatures} />
        </section>
      )}

      {/* ── CLI ── */}
      {show('cli', cliCommands.length > 0) && (
        <section id="guide-cli" className="mb-10 scroll-mt-24">
          <SectionHeader id="cli" title="In the terminal">
            The <Cmd>squirrel</Cmd> CLI reads the vault directly — no agent needed.
          </SectionHeader>
          <div className="space-y-2">
            {cliCommands.map((e) => (
              <CommandRow key={e.cmd} entry={e} forceOpen={searching} />
            ))}
          </div>
        </section>
      )}

      {/* ── This Web UI ── */}
      {show('web-ui', webuiFeatures.length > 0) && (
        <section id="guide-web-ui" className="mb-10 scroll-mt-24">
          <SectionHeader id="web-ui" title="In this Web UI">
            Everything here reads and writes the same Markdown files your agent uses.
          </SectionHeader>
          <FeatureList features={webuiFeatures} />
        </section>
      )}

      {/* ── Dashboard: Board & List ── */}
      {show('dashboard', showDashboard) && (
        <section id="guide-dashboard" className="mb-10 scroll-mt-24">
          <SectionHeader id="dashboard" title="The dashboard — Board & List">
            My projects has two views, switched with the <strong>List / Board</strong>{' '}
            toggle in the header. <strong>Board</strong> is a pipeline you can act on;{' '}
            <strong>List</strong> is a calm vertical scan of the same data.
          </SectionHeader>

          <div className="panel p-4 mb-3">
            <h3 className="font-medium text-ink mb-1">How the columns work</h3>
            <p className="text-sm leading-relaxed text-ink-2 mb-3">
              Columns read left → right toward <strong>done</strong>: PRESSING leads as
              your focus, then projects flow by stage so the closest-to-finish sits next
              to DELIVERED. The lanes are computed from each project’s deadline, so cards
              migrate forward on their own as dates approach — and a project with no
              deadline sits in ACTIVE.
            </p>
            <ul className="space-y-2.5">
              {BOARD_COLUMNS.map((c) => (
                <li key={c.label} className="flex items-start gap-2.5">
                  <span className={`mt-1.5 shrink-0 h-2 w-2 rounded-full ${c.dot}`} aria-hidden />
                  <div className="min-w-0 text-sm leading-relaxed">
                    <span className="font-bold tracking-wide text-ink text-xs">{c.label}</span>
                    <p className="text-ink-3">{c.rule}</p>
                  </div>
                </li>
              ))}
            </ul>
            <p className="text-sm leading-relaxed text-ink-3 mt-3 pt-3 border-t border-hairline">
              Drag a card between lanes to change its deadline — a confirmation dialog
              shows exactly what will change before anything is written. Dragging a
              PRESSING card into a lane defers it; PRESSING itself is computed and never
              a drop target. The same legend lives behind the board’s “?” button.
            </p>
          </div>

          <div className="panel p-4 text-sm leading-relaxed text-ink-2">
            <h3 className="font-medium text-ink mb-1">The List view</h3>
            <p>
              The same projects as a single column: pressing items on top (with their
              urgency chips), then every project with its deadline, progress, and last
              activity. Nothing is draggable here — it’s for reading, not rearranging.
              Click any row to open the project.
            </p>
          </div>
        </section>
      )}

      {/* ── FAQ ── */}
      {show('faq', faqEntries.length > 0) && (
        <section id="guide-faq" className="mb-4 scroll-mt-24">
          <SectionHeader id="faq" title="Frequently asked">
            Short answers to the things people ask first.
          </SectionHeader>
          <div className="space-y-2">
            {faqEntries.map((f) => (
              <details key={f.q} className="group panel" open={searching || undefined}>
                <summary className="flex items-center gap-2.5 px-3 py-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                  <span className="material-icons text-base text-ink-4 transition-transform duration-150 group-open:rotate-90">
                    chevron_right
                  </span>
                  <span className="text-sm text-ink-2">{f.q}</span>
                </summary>
                <div className="px-3 pb-3 pl-10 space-y-2 text-sm leading-relaxed text-ink-2">
                  {f.body}
                </div>
              </details>
            ))}
          </div>
        </section>
      )}

      {!searching && <SectionPager active={active} onNavigate={selectSection} />}
        </div>
      </div>
    </div>
  );
}
