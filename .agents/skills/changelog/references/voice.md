# Changelog voice & mapping (Squirrel)

## Scope → surface map

Squirrel commits are scoped `type(scope):`. Map the scope to a user surface:

| Scope(s) | Surface |
|---|---|
| `cli`, `installer`, `build-pkg`, `migrate-vault` | ⌨️ **CLI** |
| `desktop`, `tray`, `notif-branding`, `reminder-daemon` | 🖥 **Desktop app** |
| `web-ui`, `backend`, `guide` | 🌐 **Web UI** |
| `onboarding`, `projects`, *(unscoped product feat)* | ✨ **General** |

When a commit touches more than one surface, place it under the surface the
**user notices it in**, not where the code lives. Example: a backend fix that
makes the Web UI behave correctly → Web UI.

## Drop list (never appears in the changelog)

These are mechanism-only; they have no user-facing outcome:

- `chore:` anything (version bumps, dep bumps with no behavior change)
- `test:` / test-only changes
- `ci:` / `build:` — **unless** it changes what the user installs or runs
- `refactor`, "Refactor code structure for improved readability…"
- Any graphify commit: "refresh graphify", "Add .graphify_extract.json", `docs(graphify)`
- "update version to x", "bump to x", VERSION/package.json bumps
- `docs(spec)`, `docs(notif-branding)` and other internal doc back-fills
- Pure audit-ID commits where the fix has no observable effect for users

## Strip from surviving lines

Even on commits that DO make the cut, remove the engineering residue:

- Audit IDs: `(M6, M7)`, `(H2)`, `(M10-M13, L15)` → delete
- PR numbers `(#1234)`, author `@handles`, commit hashes
- Scope prefixes (`fix(cli):`) — the surface section already conveys this
- Internal mechanism nouns ("rglob/path join", "fsync helper", "LIMIT param")
  → translate to the effect, or drop if there is none

## Tone rules

- **Benefit-first.** Lead with what the user can now do / what now works.
- **One sentence per line.** No trailing rationale paragraphs.
- **Present tense, plain words.** "Reminders fire on time" not "Fixed an issue
  where reminders would fire at the incorrect time due to naive datetimes."
- **Security framing:** prefix with `**Security:**` and state the hardening in
  user terms ("tokens no longer written to logs"), never the CVE/audit ID.
- **Don't pad.** A version with two real changes gets two lines.
- ADHD-friendly: scannable, bold lead-ins for the standout items, no walls.
