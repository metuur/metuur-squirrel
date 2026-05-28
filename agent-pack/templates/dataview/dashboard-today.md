---
title: Today's Focus
type: dashboard
updated: daily
---

# 🧠 Today's Focus

## 🔥 Overdue / Critical (act now)

```dataview
TABLE WITHOUT ID
  "⚠️ " + file.link AS Intent,
  deadline AS Deadline,
  estado AS Estado,
  proyecto AS Proyecto
FROM "01-Proyectos-Activos"
WHERE deadline <= date(today) AND estado != "done" AND estado != "completado" AND estado != "archived"
SORT deadline ASC
```

## 🟠 Due in 24 hours

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  prioridad AS Prioridad,
  proyecto AS Proyecto
FROM "01-Proyectos-Activos"
WHERE deadline > date(today) AND deadline <= date(today) + dur(1 day)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

## 🎯 Active Intents (in-progress)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  deadline AS Deadline,
  file.mtime AS "Last Modified"
FROM "01-Proyectos-Activos"
WHERE estado = "in-progress" OR estado = "en-progreso"
SORT file.mtime DESC
LIMIT 5
```

## 📅 Due this week

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  estado AS Estado,
  prioridad AS Prioridad
FROM "01-Proyectos-Activos"
WHERE deadline > date(today) + dur(1 day)
  AND deadline <= date(today) + dur(7 days)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

---
*Refresh: reopen this note. Run `squirrel deadlines --level critical,urgent` in terminal for live data.*
