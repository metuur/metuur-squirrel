---
title: Sessions & Shutdown Notes
type: dashboard
---

# 🔄 Sessions & Shutdown Notes

## 🟢 Active / In Progress

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  file.mtime AS "Last Touched",
  deadline AS Deadline
FROM "01-Proyectos-Activos"
WHERE status = "in-progress"
SORT file.mtime DESC
```

## 🕐 Recently Modified (last 7 days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  status AS Status,
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
  project AS Project,
  file.mtime AS "Last Modified"
FROM "01-Proyectos-Activos"
WHERE status = "blocked"
SORT file.mtime DESC
```

## 💤 Stale (in-progress but not touched in 7+ days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  file.mtime AS "Last Modified",
  deadline AS Deadline
FROM "01-Proyectos-Activos"
WHERE (status = "in-progress")
  AND file.mtime < date(today) - dur(7 days)
SORT file.mtime ASC
```

## 📊 By Project — Intent Completion

```dataview
TABLE WITHOUT ID
  project AS Project,
  length(filter(rows, (r) => r.status = "done")) AS Done,
  length(filter(rows, (r) => r.status = "in-progress")) AS Active,
  length(filter(rows, (r) => r.status = "pending")) AS Pending
FROM "01-Proyectos-Activos"
WHERE project != null
GROUP BY project
SORT length(filter(rows, (r) => r.status = "in-progress")) DESC
```

---
*Terminal: `squirrel status` for live WIP view. `squirrel recover` to find interrupted sessions.*
