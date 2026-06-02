---
title: Squirrel Kanban — Weekly Review
type: dashboard
updated: weekly
---

# 🐿️ Squirrel — Weekly Review

> Use for weekly retrospective. Not a daily driver — see `Dashboard.md` for that.

---

## 📋 Pending (not started)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  deadline AS Deadline,
  priority AS Priority
FROM "01-Proyectos-Activos"
WHERE status = "pending"
SORT deadline ASC NULLS LAST
```

## 🔄 In Progress

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  deadline AS Deadline,
  file.mtime AS "Last Touch"
FROM "01-Proyectos-Activos"
WHERE status = "in-progress"
SORT file.mtime DESC
```

## 🚧 Blocked

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  file.mtime AS "Blocked Since"
FROM "01-Proyectos-Activos"
WHERE status = "blocked"
SORT file.mtime ASC
```

## ✅ Done This Month

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  file.mtime AS "Completed"
FROM "01-Proyectos-Activos" OR "04-Archivo"
WHERE (status = "done")
  AND file.mtime >= date(today) - dur(30 days)
SORT file.mtime DESC
```

---

## 📊 Progress by Project

```dataview
TABLE WITHOUT ID
  project AS Project,
  length(filter(rows, (r) => r.status = "done")) AS "✅ Done",
  length(filter(rows, (r) => r.status = "in-progress")) AS "🔄 Active",
  length(filter(rows, (r) => r.status = "blocked")) AS "🚧 Blocked",
  length(filter(rows, (r) => r.status = "pending")) AS "⏳ Pending"
FROM "01-Proyectos-Activos"
WHERE project != null AND type = "intent"
GROUP BY project
SORT length(filter(rows, (r) => r.status = "in-progress")) DESC
```

## 🏗️ Active Projects

```dataview
TABLE WITHOUT ID
  file.link AS Project,
  objective AS Objective,
  deadline AS Deadline
FROM "01-Proyectos-Activos"
WHERE type = "project"
  AND (status = "wip" OR status = "active" OR status = "in-progress")
SORT deadline ASC NULLS LAST
```

---

*Terminal: `squirrel status` for live view. `/sq-brief` for stakeholder summary.*
