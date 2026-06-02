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
WHERE type = "project"
  AND (status = "wip" OR status = "active" OR status = "in-progress")
SORT deadline ASC NULLS LAST
```

## 📈 Intent Progress by Project

```dataview
TABLE WITHOUT ID
  project AS Project,
  length(filter(rows, (r) => r.status = "done")) AS "✅ Done",
  length(filter(rows, (r) => r.status = "in-progress")) AS "🔄 Active",
  length(filter(rows, (r) => r.status = "pending")) AS "⏳ Pending",
  length(rows) AS Total
FROM "01-Proyectos-Activos"
WHERE project != null AND type = "intent"
GROUP BY project
SORT length(filter(rows, (r) => r.status = "in-progress")) DESC
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
WHERE type = "area"
SORT file.mtime ASC
```

## ⚠️ At Risk (approaching WIP limit or stale)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  deadline AS Deadline,
  file.mtime AS "Last Modified"
FROM "01-Proyectos-Activos"
WHERE (status = "in-progress")
  AND file.mtime < date(today) - dur(5 days)
  AND (deadline <= date(today) + dur(7 days) OR deadline = null)
SORT deadline ASC NULLS LAST
```

## ✅ Completed This Month

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
*Terminal: `squirrel status` for live project view. `squirrel deadlines` for deadline matrix.*
