# Web UI Guide Page — EARS Specifications

> _Backfilled from the as-built `apps/backend/app/src/pages/GuidePage.tsx`._

## Unit 1: Sections & content

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL render a Guide page containing the sections: Concepts, Configuration, A typical day, Agent commands, Desktop popup, Menu bar, CLI, Web UI, Dashboard, and FAQ. |
| R-1.2 | THE SYSTEM SHALL render each agent and CLI command as a collapsible row showing its summary, what it does, and a concrete example. |
| R-1.3 | THE SYSTEM SHALL render the desktop popup, menu-bar, and Web UI feature lists, and a dashboard board/list explainer that mirrors the board legend. |
| R-1.4 | THE SYSTEM SHALL render the page entirely from static page data without any backend request, so it works before a vault is configured. |
| R-1.5 | THE SYSTEM SHALL keep the displayed commands consistent with `agent-pack/commands/` and the `squirrel` CLI. |

## Unit 2: Live search

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the user types in the search box, THE SYSTEM SHALL filter every section simultaneously to items whose text matches the query (case-insensitive). |
| R-2.2 | WHILE a search is active, THE SYSTEM SHALL display the number of matches across all sections. |
| R-2.3 | WHEN a search matches nothing, THE SYSTEM SHALL show an explicit empty state with a "Clear search" action. |
| R-2.4 | WHILE a search is active, THE SYSTEM SHALL expand command and FAQ rows so the matched content is visible without a further click. |
| R-2.5 | THE SYSTEM SHALL make non-text illustration sections (concept map, lifecycles) searchable via associated keyword haystacks. |
| R-2.6 | WHEN the user presses Escape or clears the search, THE SYSTEM SHALL return to single-section navigation. |

## Unit 3: Section navigation

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHILE no search is active, THE SYSTEM SHALL show one selected section at a time, chosen from the quick-jump sub-sidebar. |
| R-3.2 | WHEN the user selects a section chip, THE SYSTEM SHALL show that section, clear any active search, and scroll the content to top. |
| R-3.3 | WHILE a search is active, THE SYSTEM SHALL override the section selection and render every section that has a match. |
| R-3.4 | THE SYSTEM SHALL indicate the active section in the sub-sidebar (e.g. `aria-current`). |

## Unit 4: Reachability

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL make the same guide content reachable from the desktop popup's "?" control and the menu-bar "How to use Squirrel" entry. |
| R-4.2 | THE SYSTEM SHALL render command chips as copy-selectable monospace text. |
