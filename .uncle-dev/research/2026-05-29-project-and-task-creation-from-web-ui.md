# Research: Creating Projects and Project Tasks from the Web UI

**Date:** 2026-05-29  
**Question:** How can projects and project tasks (intents) be created from the Web UI?  
**Answer in one line:** They cannot — project and intent creation is explicitly excluded from the Web UI scope and currently only available via CLI skills.

---

## 1. What the Web UI / Desktop App Support

### Desktop App (Tauri popup)
**File:** `apps/desktop/src/api/client.ts`

The popup exposes exactly these write operations:

| Endpoint | Method | What it creates |
|---|---|---|
| `/api/notes` | POST | A capture/note appended to an existing project |
| `/api/focus/{slot}` | PUT | Assigns an existing intent to today's / week's focus slot |

No project or intent creation of any kind.

### Browser SPA (backend at `http://127.0.0.1:3939`)
**File:** `docs/legacy/v0.5/docs/ears/web-ui-simple.md:39-41`

Supports:
- `POST /api/note` — create a capture note (R-3.1)
- `POST /api/note/{id}` — edit a note (R-3.2)
- `POST /api/project/{slug}` — edit an existing project's metadata (R-3.3)

Still no project creation or intent creation.

---

## 2. Explicit Non-Goals in the Specs

**`docs/legacy/v0.5/docs/hld/web-ui-simple.md:36-37`:**
> N7 — Vault structure mutations from the UI. No creating projects, no renaming folders, no moving files between PARA categories from the UI. Project creation happens via `/sq-init --add-vault` or by the user creating a folder in their vault.

**`docs/lld/phase-2-data-plane-and-desktop-popup.md:172`:**
> Backend writes from the popup beyond `/api/notes` capture (no project create, no settings, no theme — all reachable in the browser SPA)

**`docs/lld/web-ui-simple.md:297`:**
> Folder / project creation from UI [is out of scope]

---

## 3. Where Creation Actually Lives

### Project creation
**Backend route:** `POST /api/projects` — `apps/backend/server.py:198,595-645`  
**Handler:** `api_project_create` at `server.py:595`  
**Underlying writer:** `apps/cli/lib/new_project_writer.py:240-312`

The endpoint exists in the backend and is fully functional — but no Web UI page calls it.

**Required fields:**
- `tag` — uppercase project identifier (validated by regexp `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` at `new_project_writer.py:57`)
- `tipo` — `A` | `B` | `C` (`new_project_writer.py:59`)

**Optional fields:** `deadline`, `stakeholders`, `description`, `first_intent_tag`, `first_intent_title`, `force`

**Entry points today:**
- CLI skill `/sq-new-project` → calls the backend script
- Direct `POST /api/projects` (no UI triggers this)

### Intent (task) creation
**No dedicated HTTP endpoint exists.** Intents are only created:
1. As a side-effect of `POST /api/projects` when `first_intent_tag` is provided (`server.py:633`)
2. Via the `/sq-capture` CLI skill, which writes `.md` files directly to the vault

Intent file template: `agent-pack/templates/intent.md:1-38`  
Storage path: `<vault>/01-Proyectos-Activos/<PROJECT>/<TAG>.md`

---

## 4. Authentication Model

**`apps/backend/server.py:371-379`** — Cookie `squirrel_vault` selects the active vault. No RBAC. All requests scoped to vault path via `is_path_inside()` check at `server.py:704-705`.

---

## 5. Gap Summary

| Action | CLI | Desktop popup | Browser SPA |
|---|---|---|---|
| Create project | ✅ `/sq-new-project` | ❌ | ❌ |
| Create intent/task | ✅ `/sq-capture` | ❌ | ❌ |
| Edit project metadata | — | ❌ | ✅ `POST /api/project/{slug}` |
| Capture a note | ✅ `/sq-capture` | ✅ `POST /api/notes` | ✅ |
| Assign focus | ✅ `/sq-start` | ✅ `PUT /api/focus/{slot}` | ✅ |

---

## Sources

- `apps/backend/server.py` — route table (lines 193-205), `api_project_create` (595-645)
- `apps/cli/lib/new_project_writer.py` — validation & write logic (57-312)
- `apps/desktop/src/api/client.ts` — all frontend HTTP calls (161-180)
- `apps/desktop/src/components/CaptureModal.tsx` — capture UI (1-125)
- `apps/desktop/src/components/FocusPickerModal.tsx` — focus UI (1-233)
- `docs/legacy/v0.5/docs/hld/web-ui-simple.md:36-37` — N7 non-goal
- `docs/lld/phase-2-data-plane-and-desktop-popup.md:172` — popup scope limit
- `agent-pack/templates/intent.md` — intent file structure (1-38)
