---
title: Project Health
type: dashboard
---

# 🏗️ Project Health

## 🟢 WIP — Active Projects

```dataview
TABLE WITHOUT ID
  file.link AS Project,
  objetivo AS Objetivo,
  deadline AS Deadline,
  length(filter(file.tasks, (t) => t.completed)) + "/" + length(file.tasks) AS Tasks
FROM "01-Proyectos-Activos"
WHERE tipo = "proyecto" OR tipo = "project"
  AND (estado = "wip" OR estado = "active" OR estado = "en-progreso")
SORT deadline ASC NULLS LAST
```

## 📈 Intent Progress by Project

```dataview
TABLE WITHOUT ID
  proyecto AS Proyecto,
  length(filter(rows, (r) => r.estado = "done" OR r.estado = "completado")) AS "✅ Done",
  length(filter(rows, (r) => r.estado = "in-progress" OR r.estado = "en-progreso")) AS "🔄 Active",
  length(filter(rows, (r) => r.estado = "pending")) AS "⏳ Pending",
  length(rows) AS Total
FROM "01-Proyectos-Activos"
WHERE proyecto != null AND tipo = "intent"
GROUP BY proyecto
SORT length(filter(rows, (r) => r.estado = "in-progress" OR r.estado = "en-progreso")) DESC
```

## 🚧 Parking Lot

```dataview
TABLE WITHOUT ID
  file.link AS Project,
  objetivo AS Objetivo,
  file.mtime AS "Last Touched"
FROM "02-Parking-Lot"
SORT file.mtime DESC
```

## 🏛️ Areas (recurring)

```dataview
TABLE WITHOUT ID
  file.link AS Area,
  frecuencia AS Frecuencia,
  file.mtime AS "Last Review"
FROM "03-Areas"
WHERE tipo = "area"
SORT file.mtime ASC
```

## ⚠️ At Risk (approaching WIP limit or stale)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  deadline AS Deadline,
  file.mtime AS "Last Modified"
FROM "01-Proyectos-Activos"
WHERE (estado = "in-progress" OR estado = "en-progreso")
  AND file.mtime < date(today) - dur(5 days)
  AND (deadline <= date(today) + dur(7 days) OR deadline = null)
SORT deadline ASC NULLS LAST
```

## ✅ Completed This Month

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
*Terminal: `squirrel status` for live project view. `squirrel deadlines` for deadline matrix.*
