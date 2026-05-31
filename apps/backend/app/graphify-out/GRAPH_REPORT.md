# Graph Report - app  (2026-05-30)

## Corpus Check
- 32 files · ~16,928 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 186 nodes · 337 edges · 11 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `45433b4d`
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

## God Nodes (most connected - your core abstractions)
1. `useFetch()` - 25 edges
2. `compilerOptions` - 18 edges
3. `api` - 17 edges
4. `useToast()` - 13 edges
5. `useMe()` - 10 edges
6. `Modal()` - 7 edges
7. `MarkdownEditor()` - 6 edges
8. `fromNow()` - 6 edges
9. `ApiError` - 6 edges
10. `scripts` - 5 edges

## Surprising Connections (you probably didn't know these)
- `HomePage()` --calls--> `useFetch()`  [EXTRACTED]
  src/pages/HomePage.tsx → src/hooks/useFetch.ts
- `Header()` --calls--> `useCapture()`  [EXTRACTED]
  src/components/layout/Header.tsx → src/components/CaptureModal.tsx
- `CaptureDialog()` --calls--> `useToast()`  [EXTRACTED]
  src/components/CaptureModal.tsx → src/components/Toast.tsx
- `CaptureDialog()` --calls--> `useFetch()`  [EXTRACTED]
  src/components/CaptureModal.tsx → src/hooks/useFetch.ts
- `ProjectSelectorModal()` --calls--> `useFetch()`  [EXTRACTED]
  src/components/ProjectSelectorModal.tsx → src/hooks/useFetch.ts

## Communities (11 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (17): ApiError, NewIntentRequest, NewProjectRequest, MarkdownEditor(), Props, NewProjectModal(), Props, NewTaskModal() (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (12): headlessClaude(), ManualPick, PressingItem, slashCommands, useCapture(), PromptPanel(), Props, fromNow() (+4 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (21): dependencies, marked, @mdxeditor/editor, react, react-dom, react-router-dom, devDependencies, @types/react (+13 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (20): CaptureResult, CheckinResult, CheckoutResult, DeadlineGroup, FocusHistoryPayload, FocusItem, FocusPick, HistoryItem (+12 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.42
Nodes (7): api, useMe(), Header(), HeaderProps, ViewMode, Layout(), Sidebar()

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (14): ApiActivityIndicator(), CaptureCtx, CaptureDialog(), CaptureProvider(), Ctx, Mode, DeadlinesPage, HistoryPage (+6 more)

### Community 7 - "Community 7"
Cohesion: 0.19
Nodes (9): ReminderItem, RemindersPayload, RemindersWidget(), useFetch(), DeadlinesPage(), LABEL_COLORS, LABEL_ICONS, HistoryPage() (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (8): background_color, description, display, icons, name, short_name, start_url, theme_color

### Community 10 - "Community 10"
Cohesion: 0.24
Nodes (7): ProjectListItem, ConflictDialog(), Modal(), ModalProps, SIZE_CLASS, ProjectSelectorModal(), Props

## Knowledge Gaps
- **88 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+83 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useFetch()` connect `Community 7` to `Community 0`, `Community 1`, `Community 5`, `Community 6`, `Community 10`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `api` connect `Community 5` to `Community 0`, `Community 1`, `Community 3`, `Community 6`, `Community 7`, `Community 10`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `useToast()` connect `Community 0` to `Community 1`, `Community 6`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _88 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0928030303030303 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.1380952380952381 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._