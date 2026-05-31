---
title: Squirrel Dashboard
type: dashboard
updated: daily
---

# 🐿️ Squirrel — Daily Focus

> Pin this pane in Obsidian for always-visible context state.

---

## 💀 Overdue — Act Now

```dataview
TABLE WITHOUT ID
  "⚠️ " + file.link AS Intent,
  deadline AS Deadline,
  estado AS Estado,
  proyecto AS Proyecto
FROM "01-Proyectos-Activos"
WHERE deadline < date(today)
  AND estado != "done" AND estado != "completado" AND estado != "archived"
SORT deadline ASC
```

## 🔥 Due Today / Tomorrow

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  prioridad AS Prioridad,
  proyecto AS Proyecto
FROM "01-Proyectos-Activos"
WHERE deadline >= date(today) AND deadline <= date(today) + dur(1 day)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

## 🔄 Active Right Now (in-progress)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  deadline AS Deadline,
  file.mtime AS "Last Touch"
FROM "01-Proyectos-Activos"
WHERE estado = "in-progress" OR estado = "en-progreso"
SORT file.mtime DESC
LIMIT 5
```

## 📅 Due This Week

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  estado AS Estado,
  proyecto AS Proyecto
FROM "01-Proyectos-Activos"
WHERE deadline > date(today) + dur(1 day)
  AND deadline <= date(today) + dur(7 days)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

## 🚧 Blocked

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  file.mtime AS "Since"
FROM "01-Proyectos-Activos"
WHERE estado = "blocked" OR estado = "bloqueado"
SORT file.mtime ASC
```

## 💤 Stale (in-progress, untouched 7+ days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  file.mtime AS "Last Modified",
  deadline AS Deadline
FROM "01-Proyectos-Activos"
WHERE (estado = "in-progress" OR estado = "en-progreso")
  AND file.mtime < date(today) - dur(7 days)
SORT file.mtime ASC
```

## ✅ Completed This Week

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  file.mtime AS "Completed"
FROM "01-Proyectos-Activos" OR "04-Archivo"
WHERE (estado = "done" OR estado = "completado")
  AND file.mtime >= date(today) - dur(7 days)
SORT file.mtime DESC
LIMIT 10
```

---

*Terminal: `squirrel status` · `squirrel deadlines --level critical,urgent` · `/sq-where-am-i`*
