# Native Notification Banner (with Deep-Link to Tauri Popup) — Low-Level Design

## Architecture

```
Native Notification Banner — touched components only

User's macOS host
│
├── ~/.squirrel/
│   ├── config.toml                       [unchanged]
│   ├── reminders-state.json              [schema unchanged; `snoozed_until`
│   │                                       write path retired by banner emitter]
│   └── reminders-daemon.log              [new tags: banner,
│                                           banner-fallback-osascript,
│                                           banner-fallback-dialog,
│                                           terminal-notifier-missing,
│                                           permission-denied,
│                                           deep-link-handled,
│                                           deep-link-dropped,
│                                           deep-link-unknown-host,
│                                           deep-link-bad-path]
│
├── agent-pack/companions/macos-reminders/
│   │   (shipped source; mirrored to the launchd-installed copy at
│   │    ~/others/ai-agents/adhd-context-bridge/companions/macos-reminders/)
│   └── reminder-daemon.sh                [HEAVILY TOUCHED]
│       ├── emit_banner(project, ntitle, subtitle, body)       [NEW]
│       │     # 1. compose deep-link URL via compose_deeplink
│       │     # 2. try show_notification_terminal_notifier
│       │     # 3. fallback show_notification_osascript
│       │     # 4. fallback show_dialog_fallback
│       │     # echoes back the path actually used (banner /
│       │     # banner-fallback-osascript / banner-fallback-dialog)
│       ├── show_notification_terminal_notifier(...)            [NEW]
│       │     # invokes terminal-notifier with -title, -subtitle,
│       │     # -message, -open, -sender com.metuur.squirrel,
│       │     # -group org.squirrel.reminders, -sound Submarine
│       ├── show_notification_osascript(...)                    [NEW]
│       │     # osascript -e 'display notification ...'
│       │     # (no -open equivalent; click is a no-op)
│       ├── show_dialog_fallback(...)                           [NEW]
│       │     # last-resort: osascript display dialog with a
│       │     # single OK button and a "notifications disabled"
│       │     # warning prepended to the body
│       ├── compose_deeplink(project, task) -> string           [NEW]
│       │     # if project is empty AND task non-empty: use task as project
│       │     #   (legacy path; rare — scanner items always carry project)
│       │     # if task is empty OR task == project:
│       │     #   echo "squirrel://projects/${project}"
│       │     # else:
│       │     #   echo "squirrel://projects/${project}/${task}"
│       ├── show_dialog                                          [REMOVED]
│       ├── open_in_web_ui                                       [REMOVED]
│       └── update_state_after_dialog                            [RENAMED →
│             update_state_after_emit, no-Snooze branch removed]
│
├── apps/desktop/src-tauri/Cargo.toml                          [TOUCHED]
│   └── + tauri-plugin-deep-link = "2"                          [NEW dep]
│
├── apps/desktop/src-tauri/tauri.conf.json                     [TOUCHED]
│   └── + plugins.deep-link.desktop.schemes = ["squirrel"]      [NEW]
│
├── apps/desktop/src-tauri/capabilities/default.json           [TOUCHED]
│   └── + "deep-link:default" capability                        [NEW]
│
├── apps/desktop/src-tauri/src/lib.rs                          [TOUCHED]
│   ├── + .plugin(tauri_plugin_deep_link::init())               [NEW, near line 39]
│   └── + tauri::Builder::on_open_url handler                   [NEW]
│         # parse URL → delegate to deep_link::handle
│
├── apps/desktop/src-tauri/src/deep_link.rs                    [NEW MODULE]
│   ├── pub struct Target { project_id: String, task_id: Option<String> }
│   ├── pub fn handle<R: Runtime>(app: &AppHandle<R>, url: Url) -> tauri::Result<()>
│   │     # 1. require url.scheme() == "squirrel"
│   │     # 2. require url.host_str() == Some("projects")
│   │     # 3. require 1 or 2 path segments, each matching [A-Za-z0-9_-]+
│   │     # 4. surface the popup window (existing helper in tray.rs
│   │     #    or window-management utility)
│   │     # 5. app.emit("deep-link://focus-project",
│   │     #            { projectId: <seg-1>, taskId: <seg-2 | null> })
│   ├── fn validate(url: &Url) -> Result<Target, DeepLinkError>
│   └── #[cfg(test)] mod tests
│         # accept squirrel://projects/FOO
│         #     → Target { project_id: "FOO", task_id: None }
│         # accept squirrel://projects/FOO/BAR
│         #     → Target { project_id: "FOO", task_id: Some("BAR") }
│         # reject http://projects/FOO       (bad scheme)
│         # reject squirrel://focus/FOO      (bad host)
│         # reject squirrel://projects/      (no segments)
│         # reject squirrel://projects/FOO/BAR/BAZ (3 segments)
│         # reject squirrel://projects/FO O  (illegal chars in seg-1)
│         # reject squirrel://projects/FOO/B R (illegal chars in seg-2)
│
├── apps/desktop/src/App.tsx                                   [TOUCHED]
│   └── + useDeepLink() hook subscription                       [NEW]
│         # listens for "deep-link://focus-project" event;
│         # passes scrollTarget={id, key} down to DeadlinesWidget
│
├── apps/desktop/src/hooks/useDeepLink.ts                      [NEW]
│   ├── type FocusTarget = { projectId: string; taskId: string | null; key: number }
│   ├── const [target, setTarget] = useState<FocusTarget | null>(null)
│   ├── const keyRef = useRef(0)
│   ├── useEffect: listen('deep-link://focus-project', ({ payload }) => {
│   │      keyRef.current += 1
│   │      setTarget({
│   │        projectId: payload.projectId,
│   │        taskId: payload.taskId ?? null,
│   │        key: keyRef.current,
│   │      })
│   │   })
│   └── return target
│
├── apps/desktop/src/components/DeadlinesWidget.tsx            [TOUCHED]
│   ├── new prop: scrollTarget?: FocusTarget | null
│   ├── const cardRefs = useRef<Record<string, HTMLDivElement | null>>({})
│   ├── each rendered card gets:
│   │       id={`deadline-card-${item.id}`}
│   │       data-task-id={item.id}
│   │       data-project-id={projectForTask(item.id, projects)?.slug ?? ""}
│   │       ref={(el) => { cardRefs.current[item.id] = el }}
│   │       data-highlight={highlightedId === item.id ? "on" : undefined}
│   └── useEffect(() => {
│       if (!scrollTarget) return
│       // Prefer exact task match. Fall back to first card whose project matches.
│       let el: HTMLDivElement | null = null
│       if (scrollTarget.taskId) {
│         el = cardRefs.current[scrollTarget.taskId] ?? null
│       }
│       if (!el) {
│         el = Object.values(cardRefs.current).find(
│           (n) => n?.dataset.projectId === scrollTarget.projectId
│         ) ?? null
│       }
│       if (!el) { console.debug("deep-link target not in list", scrollTarget); return }
│       el.scrollIntoView({ block: "center", behavior: "smooth" })
│       const matchedId = el.dataset.taskId ?? null
│       if (matchedId) setHighlightedId(matchedId)
│       const t = setTimeout(() => setHighlightedId(null), 1500)
│       return () => clearTimeout(t)
│   }, [scrollTarget?.key])
│
├── apps/desktop/src/components/DeadlinesWidget.module.css     [NEW]
│   └── [data-highlight="on"] { animation: squirrel-highlight 1.5s ease-out; }
│       @keyframes squirrel-highlight {
│           0%   { background-color: rgba(253, 224, 71, 0.0); }
│           15%  { background-color: rgba(253, 224, 71, 0.55); }
│           70%  { background-color: rgba(253, 224, 71, 0.30); }
│           100% { background-color: rgba(253, 224, 71, 0.0); }
│       }
│
└── (external)
    └── terminal-notifier                                       [Homebrew dep, optional]
          # brew install terminal-notifier
          # Invocation shape (-sender now included; delivered by
          # notification-icon-branding, see EARS R-1.6 / R-1.10):
          #   terminal-notifier \
          #     -title    "⏰ squirrel: <PROJECT-ID>" \
          #     -subtitle "<due-status>" \
          #     -message  "<note title · → <next-action>>" \
          #     -open     "squirrel://projects/<PROJECT-ID>" \
          #     -group    org.squirrel.reminders \
          #     -sender   com.metuur.squirrel \
          #     -sound    Submarine
```

## Constraints

1. **macOS only.** No fallback abstraction for Linux/Windows hosts.
2. **`terminal-notifier` is optional, not mandatory.** Detection: `command -v terminal-notifier`. Missing → osascript banner. Click-to-open is lost in that path but the alert still happens.
3. **No new always-on processes.** `terminal-notifier` is a per-emission shell-out; the Tauri deep-link handler runs in-process; the React listener is a one-time `tauri-event` subscription mounted with `App`.
4. **State-file backward compatibility.** `~/.squirrel/reminders-state.json` retains the existing keys: `last_shown`, `dialogs_date`, `dialogs_today`, optional `snoozed_until`. The banner emitter stops writing `snoozed_until` (no Snooze button to trigger it) but does not delete a pre-existing value (forward-compat with any future button-bearing emitter).
5. **No new permissions in `capabilities/default.json`** beyond `deep-link:default`. Notification permission for `terminal-notifier` is system-granted by the user (orthogonal to Squirrel's capability set).
6. **`com.metuur.squirrel` is the bundle identifier** (confirmed in `tauri.conf.json`). `terminal-notifier -sender com.metuur.squirrel` makes the banner appear as "from" Squirrel — same icon, same notification group in System Settings, same Focus-mode rules.
7. **URL scheme `squirrel://`.** All-lowercase. Two valid shapes:
   - `squirrel://projects/<project-id>` — 1 path segment after host (project landing).
   - `squirrel://projects/<project-id>/<task-id>` — 2 path segments (specific task within project).
   Any other shape (different host, 0 or 3+ segments, illegal characters) is logged and dropped.
8. **Deep-link event schema.** Tauri event name: `deep-link://focus-project`. Payload: `{ projectId: string, taskId: string | null }`. The React side never reads the raw URL.
9. **Highlight duration.** 1500 ms total via CSS keyframes (`squirrel-highlight`). `background-color` only, GPU-friendly, no layout thrash.
10. **The popup is short-lived.** It may close after the user clicks away. The deep-link path must work whether the popup was already open or just opened by the URL scheme — see R-4.2, R-4.3.

## Key Decisions

### D-1. `terminal-notifier` as the primary emitter

Rejected alternatives:

- **`alerter`.** More actively maintained, but it has the same `-actions` deprecation pattern as `terminal-notifier`; binary is larger; no significant advantage for our static-URL click target.
- **`tauri-plugin-notification` direct from the daemon.** Would require the daemon to make an HTTP POST to a new backend endpoint, which would then dispatch the notification via Tauri. Adds two failure modes (backend down; HTTP timeout) and a tight coupling between launchd schedule and Tauri-popup-must-be-running. Reserved for a future change.
- **Native macOS `osascript display notification` only.** Doesn't support a click handler. Acceptable as fallback, not primary.
- **Custom Swift binary.** Overkill; introduces a new build step and code-signing surface.

`terminal-notifier` is the best balance: zero-build, brew-installable, supports `-open URL` (which works with custom `squirrel://` schemes), `-sender` (so branding is correct), and is widely used despite the upstream being frozen since 2019. Its unmaintained status is an accepted risk; if it breaks on a future macOS, the daemon falls back to the osascript banner (no click target) and the user can pin to a working brew version.

### D-2. URL scheme shape: nested `squirrel://projects/<p>/<t>`

Chosen because the daemon's scanner items are typed (`project` is the project tag, `id` is the intent / task slug), and a single URL family that scales from project-only to project-plus-task lets us pick the right scope at compose time without inventing a separate `tasks` host. Examples:

- `squirrel://projects/CASA-CONTABILIDAD-TAXES-2025` — opens the project's first deadline card.
- `squirrel://projects/CASA-CONTABILIDAD-TAXES-2025/test-deadline` — opens the specific task within that project.

Rejected alternatives:

- `squirrel://focus/<id>` — `focus` is overloaded (FocusWidget pick vs. deep-link focus).
- Separate `squirrel://tasks/<task-id>` host — drops the project context that the React side needs as a fallback when the specific task is no longer in the pressing list.
- `squirrel:///projects/<id>` (no host, all-in-path) — `tauri-plugin-deep-link` and `url::Url::host_str()` parse the `projects` token as host in the chosen form, which simplifies validation.
- Query string `squirrel://open?type=project&id=X&task=Y` — overkill; risks URL-encoding ambiguity on special characters.

The single host `projects` + 1-or-2 path segments leaves room for future top-level routes (`squirrel://notes/<id>`, `squirrel://deadlines`) without colliding.

### D-3. Scroll-and-highlight, not filter or detail view

Rejected:

- **Filter the dashboard to one project.** Adds clearable state to the popup (where does "clear filter" live?); gets stale fast (other items still useful as context); the user already arrived with banner-given context.
- **Detail view.** No detail view exists in the popup today; adding one is a much larger UX change. The popup is the dashboard; the web UI is the detail.

Scroll-and-highlight gives the "the banner pointed me here" affordance without introducing state or a new view.

### D-4. Permission-denied → modal dialog fallback (not silent skip)

Silently skipping when notification permission is denied would leave the user with no alert and the daemon appearing broken. Falling back to a `display dialog`:

- Preserves the alert reliably (`display dialog` does not need notification permission).
- Is clearly labelled with `⚠️ Notifications are disabled — fallback to dialog.` so the user knows to flip a System Settings toggle.
- The fallback dialog has a single `OK` button (no Snooze/Open) to keep code lean.

### D-5. `update_state_after_dialog` → `update_state_after_emit`, no Snooze branch

Snooze was a UI button on the modal dialog. Banners have no buttons. The function previously branched on `choice`; now it always behaves as "Shown":

- Updates `last_shown`, `dialogs_today`, `dialogs_date` exactly as before.
- Does NOT write `snoozed_until` (no Snooze button to set it).
- Leaves any pre-existing `snoozed_until` value untouched (forward-compat with a future button-bearing emitter).

The implicit-snooze is the existing `cadence_minutes` throttle — invariant.

### D-6. `terminal-notifier -sender com.metuur.squirrel` — DELIVERED (see `notification-icon-branding`)

With `-sender com.metuur.squirrel`:

- The banner uses the Squirrel app icon.
- macOS treats it as coming from the Squirrel app — same notification group in System Settings, same Focus-mode rules.
- The user grants/revokes notification permission for "Squirrel" specifically rather than for the script-runner.

**Status: delivered by `docs/{hld,lld,ears}/notification-icon-branding.md`.** Validated on macOS 26.5 + `terminal-notifier` 2.0.0 that `-sender com.metuur.squirrel` silently drops the banner until `com.metuur.squirrel` has emitted at least one notification through Apple's modern `UNUserNotificationCenter` API. `terminal-notifier` uses the deprecated `NSUserNotificationCenter` path, and the bridge no longer auto-registers unknown senders on Big Sur+; `-appIcon`/`-contentImage` are likewise silently ignored on macOS 11+. The branding change satisfies the precondition with a permission-gated, one-shot Tauri-side `tauri-plugin-notification` emission on first launch (branding Unit 1) — that emission registers the bundle with `UNUserNotificationCenter`, surfaces "Squirrel" in System Settings → Notifications, and unlocks `-sender` for the daemon (branding R-2.1). Note the **cold-identity window** (branding R-4.5) and the **reinstall requirement** for existing daemons (branding R-2.5). See EARS R-1.6 / R-1.10.

### D-7. New module `deep_link.rs`, not extending `tray_alerts.rs`

`tray_alerts.rs` polls and updates the menu. The deep-link path is event-driven and emits a Tauri event the React side consumes. Different concerns, different modules. Future deep-link routes (`squirrel://notes/<id>`) extend `deep_link.rs` without touching tray.

### D-8. `useDeepLink` hook with a monotonic `key`

Using `id` alone as the state value would prevent re-firing the effect when the same banner is clicked twice (React skips state updates when the value is identical). A monotonically incrementing `key` ensures the effect re-runs every time, which is what we want (re-scroll, re-highlight). The `key` is internal — not exposed to consumers and not persisted.

### D-9. Daemon emits the deep-link URL even when using the no-click fallback

When `terminal-notifier` is missing and we fall back to `osascript display notification`, the deep-link URL is composed but not passed (osascript doesn't accept it). The composition is cheap and idempotent; isolating "should I compose the URL?" from "can the emitter use it?" keeps the emitter functions narrow and uniform.

## Out of Scope

- Cross-process IPC between the daemon and the Tauri app for emit/ack handshakes. Today's flow is fire-and-forget; click is OS-mediated via the URL scheme.
- Persisting a "last clicked deadline" anywhere.
- Custom keyframe library or animation framework — plain CSS keyframes suffice.
- A banner-event log in `~/.squirrel/` beyond the existing daemon log.
- Replacing the Phase-2 tray menu's "PRESSING NOW" surface.
- Migrating the daemon to a Tauri-side scheduler (would unify scheduling under the desktop app; reserved for a separate change).
- Adding `terminal-notifier` to `apps/desktop/scripts/post-install.sh` or the Tauri bundle. The user installs it themselves; the daemon detects.
- Tray icon state transitions on banner emit. Tray icon stays `Normal` unless `tray_alerts.rs` says otherwise.
- A "notification log" UI in the popup. The Notification Center is the log.
- Banner click that opens the **web UI in the browser** when the popup is not running. macOS will launch the Squirrel app per the URL scheme registration; if Squirrel cannot launch (binary moved, codesign broken), macOS shows its own error — no daemon-side recovery.
