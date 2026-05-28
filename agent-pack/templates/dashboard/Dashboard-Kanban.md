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
  proyecto AS Proyecto,
  deadline AS Deadline,
  prioridad AS Prioridad
FROM "01-Proyectos-Activos"
WHERE estado = "pending" OR estado = "pendiente"
SORT deadline ASC NULLS LAST
```

## 🔄 In Progress

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  deadline AS Deadline,
  file.mtime AS "Last Touch"
FROM "01-Proyectos-Activos"
WHERE estado = "in-progress" OR estado = "en-progreso"
SORT file.mtime DESC
```

## 🚧 Blocked

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  file.mtime AS "Blocked Since"
FROM "01-Proyectos-Activos"
WHERE estado = "blocked" OR estado = "bloqueado"
SORT file.mtime ASC
```

## ✅ Done This Month

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  file.mtime AS "Completed"
FROM "01-Proyectos-Activos" OR "04-Archivo"
WHERE (estado = "done" OR estado = "completado")
  AND file.mtime >= date(today) - dur(30 days)
SORT file.mtime DESC
```

---

## 📊 Progress by Project

```dataview
TABLE WITHOUT ID
  proyecto AS Proyecto,
  length(filter(rows, (r) => r.estado = "done" OR r.estado = "completado")) AS "✅ Done",
  length(filter(rows, (r) => r.estado = "in-progress" OR r.estado = "en-progreso")) AS "🔄 Active",
  length(filter(rows, (r) => r.estado = "blocked" OR r.estado = "bloqueado")) AS "🚧 Blocked",
  length(filter(rows, (r) => r.estado = "pending")) AS "⏳ Pending"
FROM "01-Proyectos-Activos"
WHERE proyecto != null AND tipo = "intent"
GROUP BY proyecto
SORT length(filter(rows, (r) => r.estado = "in-progress" OR r.estado = "en-progreso")) DESC
```

## 🏗️ Active Projects

```dataview
TABLE WITHOUT ID
  file.link AS Project,
  objetivo AS Objetivo,
  deadline AS Deadline
FROM "01-Proyectos-Activos"
WHERE tipo = "proyecto" OR tipo = "project"
  AND (estado = "wip" OR estado = "active" OR estado = "en-progreso")
SORT deadline ASC NULLS LAST
```

---

*Terminal: `squirrel status` for live view. `/sq-brief` for stakeholder summary.*
