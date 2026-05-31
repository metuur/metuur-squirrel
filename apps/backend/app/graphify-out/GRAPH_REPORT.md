# Graph Report - app  (2026-05-31)

## Corpus Check
- 32 files · ~16,012 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 190 nodes · 341 edges · 9 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `312905a8`
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
- [[_COMMUNITY_Community 8|Community 8]]

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
- `RemindersWidget()` --calls--> `useFetch()`  [EXTRACTED]
  src/components/RemindersWidget.tsx → src/hooks/useFetch.ts
- `Header()` --calls--> `useCapture()`  [EXTRACTED]
  src/components/layout/Header.tsx → src/components/CaptureModal.tsx
- `CaptureDialog()` --calls--> `useFetch()`  [EXTRACTED]
  src/components/CaptureModal.tsx → src/hooks/useFetch.ts
- `PromptPanel()` --calls--> `useToast()`  [EXTRACTED]
  src/components/PromptPanel.tsx → src/components/Toast.tsx

## Communities (9 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (17): ApiError, NewIntentRequest, NewProjectRequest, CaptureDialog(), ConflictDialog(), MarkdownEditor(), Props, Modal() (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (12): headlessClaude(), ManualPick, PressingItem, slashCommands, useCapture(), PromptPanel(), Props, fromNow() (+4 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (24): dependencies, marked, @mdxeditor/editor, react, react-dom, react-router-dom, @squirrel/design-system, devDependencies (+16 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (23): CaptureResult, CheckinResult, CheckoutResult, DeadlineGroup, FocusHistoryPayload, FocusItem, FocusPick, HistoryItem (+15 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.14
Nodes (18): api, ProjectListItem, ProjectSelectorModal(), Props, useFetch(), useMe(), Header(), HeaderProps (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (17): ApiActivityIndicator(), CaptureCtx, CaptureProvider(), Ctx, Mode, Ctx, Toast, ToastMsg (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (8): background_color, description, display, icons, name, short_name, start_url, theme_color

## Knowledge Gaps
- **92 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+87 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useFetch()` connect `Community 5` to `Community 0`, `Community 1`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `api` connect `Community 5` to `Community 0`, `Community 1`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `useToast()` connect `Community 0` to `Community 1`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _92 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.11264367816091954 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.1380952380952381 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._