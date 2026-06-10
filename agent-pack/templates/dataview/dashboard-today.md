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
  status AS Status,
  project AS Project
FROM "01-Active-Projects"
WHERE deadline <= date(today) AND status != "done" AND status != "done" AND status != "archived"
SORT deadline ASC
```

## 🟠 Due in 24 hours

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  priority AS Priority,
  project AS Project
FROM "01-Active-Projects"
WHERE deadline > date(today) AND deadline <= date(today) + dur(1 day)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

## 🎯 Active Intents (in-progress)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  deadline AS Deadline,
  file.mtime AS "Last Modified"
FROM "01-Active-Projects"
WHERE status = "in-progress"
SORT file.mtime DESC
LIMIT 5
```

## 📅 Due this week

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  status AS Status,
  priority AS Priority
FROM "01-Active-Projects"
WHERE deadline > date(today) + dur(1 day)
  AND deadline <= date(today) + dur(7 days)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

---
*Refresh: reopen this note. Run `squirrel deadlines --level critical,urgent` in terminal for live data.*
