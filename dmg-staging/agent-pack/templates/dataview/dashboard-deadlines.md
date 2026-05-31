---
title: Deadlines Overview
type: dashboard
---

# 📅 Deadlines Overview

## 💀 Overdue

```dataview
TABLE WITHOUT ID
  "💀 " + file.link AS Intent,
  deadline AS Deadline,
  estado AS Estado,
  proyecto AS Proyecto
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline < date(today)
  AND estado != "done" AND estado != "completado" AND estado != "archived"
SORT deadline ASC
```

## 🔴 Critical (< 4 hours)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  prioridad AS Prioridad
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline = date(today)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

## 🟠 Urgent (today–tomorrow)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  proyecto AS Proyecto,
  prioridad AS Prioridad
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) AND deadline <= date(today) + dur(1 day)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

## 🟡 Soon (2–3 days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  proyecto AS Proyecto
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) + dur(1 day)
  AND deadline <= date(today) + dur(3 days)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

## 🔵 Upcoming (4–7 days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  proyecto AS Proyecto,
  estado AS Estado
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) + dur(3 days)
  AND deadline <= date(today) + dur(7 days)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
```

## 🟢 Future (> 1 week)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  proyecto AS Proyecto,
  estado AS Estado
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) + dur(7 days)
  AND estado != "done" AND estado != "completado"
SORT deadline ASC
LIMIT 10
```

## ✅ Recently Completed

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  file.mtime AS "Completed Around"
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE (estado = "done" OR estado = "completado") AND deadline != null
SORT file.mtime DESC
LIMIT 5
```

---
*Terminal: `squirrel deadlines` for all levels, `squirrel deadlines --level critical,urgent` for urgent only.*
