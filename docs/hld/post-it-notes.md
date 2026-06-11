# Post-it Notes — High-Level Design

## Overview

Post-its are ambiguous, independent working-memory captures: a random thought, idea, reminder, quote, phone number, or fragment that the user grabs before knowing whether it is actionable or project-related. They are a distinct artifact from Quick Tasks (actionable by default, task lifecycle) and project/task notes (contextual by default, attached to known work). A Post-it starts unclassified and may stay that way indefinitely — "capture now, decide later." This feature adds a first-class Post-it model, capture surfaces in the desktop popup, tray menu, and Web UI, and a dedicated sticky-note board page where Post-its can be colored, pinned, dragged, archived, or converted into a Quick Task, project task, or project note once their meaning becomes clear.

## Stakeholders & Impact

- **The user capturing a fragment mid-focus.** Today the only fast paths force a premature decision: Quick Task capture makes it a task; note capture makes it a note (possibly attached to a project) or dumps it into `99-Resources/Inbox` as an unfiled capture. After this ships, an ambiguous fragment goes onto the Post-it wall with zero classification pressure, from the tray menu, the desktop popup, or the Web UI.
- **The user reviewing the wall later.** Today unfiled captures are buried in the Inbox folder and only resurface through search. After this ships, the `/post-its` board makes ambiguous captures visible as colored sticky cards that can be promoted to real work (Quick Task, project task, project note) or archived when no longer needed.
- **Existing flows (secondary).** Quick Tasks, project notes, journal, reminders, deadlines, focus, and home board behavior are untouched. Existing scanners must not start picking up Post-it files.

## Goals

- A Post-it can be created from: a tray menu item (opens an in-app capture modal in the desktop popup), the desktop popup UI directly, and the Web UI Post-it board page.
- Post-its persist as Markdown files in a dedicated vault folder outside any project, with frontmatter carrying their semantic state (color, label, pinned, active/archived, conversion record). Markdown is the source of truth.
- Board presentation state (free position, rotation) persists in the local SQLite database as a rebuildable index; losing it never loses content.
- The Web UI has a `/post-its` page rendering Post-its as scattered colored sticky cards (per the visual reference: sticky-note palette, slight rotation, handwritten-style text, optional small corner label) with drag-to-reposition.
- A Post-it supports: color selection, optional short corner label, pin (always surfaces on top), archive/restore (hidden without deletion), delete, and edit.
- A Post-it can be converted into a Quick Task, a project task, or a project note via existing creation flows; the Post-it records the conversion and leaves the active wall.
- Post-it content is discoverable through the existing header search, and a Post-it search hit leads back to the board.

## Non-Goals

- No global keyboard shortcut for Post-it capture in v1 (Quick Tasks keep `Ctrl+Cmd+Q`; nothing new is registered).
- No changes to Quick Task, journal, reminder, deadline, focus, or home-board behavior; Post-its do not appear on the Home board.
- No changes to the existing desktop popup note CaptureModal or Web UI CaptureModal flows — Post-it capture is a separate, parallel surface.
- Post-its never gain reminder dates, deadlines, statuses, or any scheduling in v1 — that is what conversion is for.
- No viewing/managing of the Post-it wall inside the desktop popup in v1 (capture only); the board is a Web UI surface.
- No multi-device sync or cloud storage — everything stays local-first like the rest of the product.

## Success Criteria

- From the tray menu, "Add Post-it" foregrounds the popup, the user types a fragment, presses Enter, and a Markdown file appears under the dedicated Post-it vault folder — without the web UI opening.
- Visiting `/post-its` shows every active Post-it as a colored sticky card; dragging a card and reloading the page preserves its position; deleting `squirrel.db` and reloading still shows every Post-it (default layout).
- Pinning a Post-it keeps it visually surfaced; archiving removes it from the active wall and the archived view can restore it.
- Converting a Post-it to a Quick Task makes it appear in the Quick Task stack, and the Post-it leaves the active wall with a record of where it went.
- Searching for a phrase inside a Post-it from the header returns a hit that navigates to the board.
- Quick Task listing, home summary, reminder/deadline scans, and project listings behave identically before and after Post-it files exist in the vault.
