---
title: Sessions & Shutdown Notes
type: dashboard
---

# 🔄 Sessions & Shutdown Notes

## 🟢 Active / In Progress

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  file.mtime AS "Last Touched",
  deadline AS Deadline
FROM "01-Proyectos-Activos"
WHERE estado = "in-progress" OR estado = "en-progreso"
SORT file.mtime DESC
```

## 🕐 Recently Modified (last 7 days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  estado AS Estado,
  file.mtime AS Modified
FROM "01-Proyectos-Activos"
WHERE file.mtime >= date(today) - dur(7 days)
SORT file.mtime DESC
LIMIT 15
```

## 🚧 Blocked

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  proyecto AS Proyecto,
  file.mtime AS "Last Modified"
FROM "01-Proyectos-Activos"
WHERE estado = "blocked" OR estado = "bloqueado"
SORT file.mtime DESC
```

## 💤 Stale (in-progress but not touched in 7+ days)

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

## 📊 By Project — Intent Completion

```dataview
TABLE WITHOUT ID
  proyecto AS Proyecto,
  length(filter(rows, (r) => r.estado = "done" OR r.estado = "completado")) AS Done,
  length(filter(rows, (r) => r.estado = "in-progress" OR r.estado = "en-progreso")) AS Active,
  length(filter(rows, (r) => r.estado = "pending")) AS Pending
FROM "01-Proyectos-Activos"
WHERE proyecto != null
GROUP BY proyecto
SORT length(filter(rows, (r) => r.estado = "in-progress")) DESC
```

---
*Terminal: `squirrel status` for live WIP view. `squirrel recover` to find interrupted sessions.*
