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
  status AS Status,
  project AS Project
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline < date(today)
  AND status != "done" AND status != "done" AND status != "archived"
SORT deadline ASC
```

## 🔴 Critical (< 4 hours)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  priority AS Priority
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline = date(today)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

## 🟠 Urgent (today–tomorrow)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  project AS Project,
  priority AS Priority
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) AND deadline <= date(today) + dur(1 day)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

## 🟡 Soon (2–3 days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  project AS Project
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) + dur(1 day)
  AND deadline <= date(today) + dur(3 days)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

## 🔵 Upcoming (4–7 days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  project AS Project,
  status AS Status
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) + dur(3 days)
  AND deadline <= date(today) + dur(7 days)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

## 🟢 Future (> 1 week)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  project AS Project,
  status AS Status
FROM "01-Proyectos-Activos" OR "03-Areas"
WHERE deadline > date(today) + dur(7 days)
  AND status != "done" AND status != "done"
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
WHERE (status = "done") AND deadline != null
SORT file.mtime DESC
LIMIT 5
```

---
*Terminal: `squirrel deadlines` for all levels, `squirrel deadlines --level critical,urgent` for urgent only.*
