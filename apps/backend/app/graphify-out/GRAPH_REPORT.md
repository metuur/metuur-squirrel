# Graph Report - app  (2026-06-11)

## Corpus Check
- 41 files · ~32,651 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 294 nodes · 507 edges · 12 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e5b15328`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]

## God Nodes (most connected - your core abstractions)
1. `useFetch()` - 29 edges
2. `api` - 23 edges
3. `compilerOptions` - 18 edges
4. `useToast()` - 18 edges
5. `useMe()` - 10 edges
6. `Modal()` - 8 edges
7. `ApiError` - 8 edges
8. `scripts` - 6 edges
9. `MarkdownEditor()` - 6 edges
10. `Header()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `ConfigPanel()` --calls--> `useToast()`  [EXTRACTED]
  src/pages/JournalPage.tsx → src/components/Toast.tsx
- `HomePage()` --calls--> `useFetch()`  [EXTRACTED]
  src/pages/HomePage.tsx → src/hooks/useFetch.ts
- `RemindersWidget()` --calls--> `useFetch()`  [EXTRACTED]
  src/components/RemindersWidget.tsx → src/hooks/useFetch.ts
- `Header()` --calls--> `useCapture()`  [EXTRACTED]
  src/components/layout/Header.tsx → src/components/CaptureModal.tsx
- `CaptureDialog()` --calls--> `useFetch()`  [EXTRACTED]
  src/components/CaptureModal.tsx → src/hooks/useFetch.ts

## Communities (12 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (28): ApiError, NewIntentRequest, NewProjectRequest, ReminderItem, RemindersPayload, CaptureCtx, CaptureDialog(), CaptureProvider() (+20 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (24): EntityKind, headlessClaude(), PressingItem, slashCommands, useCapture(), Markdown(), Props, PromptPanel() (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (28): dependencies, marked, @mdxeditor/editor, react, react-dom, react-markdown, react-router-dom, remark-gfm (+20 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (41): authHeaders(), call(), CaptureResult, CheckinResult, CheckoutResult, DeadlineGroup, FocusHistoryPayload, FocusItem (+33 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (18): api, asVaultRecovery(), VaultRecoveryPayload, ProjectSelectorModal(), Props, VaultRecovery(), useFetch(), useMe() (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (11): ApiActivityIndicator(), DeadlinesPage, GuidePage, HistoryPage, HomePage, JournalPage, NoteEditPage, NotePage (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (22): NotificationItem, QuickTasksPayload, SearchHit, DEFAULT_DOT_STYLE, dotStyle(), NotificationCenter(), NotifRow(), pathOf() (+14 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (8): background_color, description, display, icons, name, short_name, start_url, theme_color

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (15): AGENT_GROUPS, BOARD_COLUMNS, CLI_COMMANDS, CommandEntry, CommandGroup, CONCEPTS, DAY_STEPS, FAQ_ENTRIES (+7 more)

### Community 11 - "Community 11"
Cohesion: 0.29
Nodes (7): JournalEntry, Mood, ConfigPanel(), formatNextDue(), JournalPage(), MOOD_EMOJI, MOODS

## Knowledge Gaps
- **146 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+141 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `api` connect `Community 5` to `Community 0`, `Community 1`, `Community 3`, `Community 7`, `Community 11`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `useFetch()` connect `Community 5` to `Community 0`, `Community 1`, `Community 11`, `Community 7`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `useToast()` connect `Community 0` to `Community 1`, `Community 11`, `Community 5`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _146 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07123034227567067 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07357357357357357 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.06896551724137931 - nodes in this community are weakly interconnected._