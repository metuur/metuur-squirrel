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
  status AS Status,
  project AS Project
FROM "01-Active-Projects"
WHERE deadline < date(today)
  AND status != "done" AND status != "done" AND status != "archived"
SORT deadline ASC
```

## 🔥 Due Today / Tomorrow

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  priority AS Priority,
  project AS Project
FROM "01-Active-Projects"
WHERE deadline >= date(today) AND deadline <= date(today) + dur(1 day)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

## 🔄 Active Right Now (in-progress)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  deadline AS Deadline,
  file.mtime AS "Last Touch"
FROM "01-Active-Projects"
WHERE status = "in-progress"
SORT file.mtime DESC
LIMIT 5
```

## 📅 Due This Week

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  deadline AS Deadline,
  status AS Status,
  project AS Project
FROM "01-Active-Projects"
WHERE deadline > date(today) + dur(1 day)
  AND deadline <= date(today) + dur(7 days)
  AND status != "done" AND status != "done"
SORT deadline ASC
```

## 🚧 Blocked

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  file.mtime AS "Since"
FROM "01-Active-Projects"
WHERE status = "blocked"
SORT file.mtime ASC
```

## 💤 Stale (in-progress, untouched 7+ days)

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  file.mtime AS "Last Modified",
  deadline AS Deadline
FROM "01-Active-Projects"
WHERE (status = "in-progress")
  AND file.mtime < date(today) - dur(7 days)
SORT file.mtime ASC
```

## ✅ Completed This Week

```dataview
TABLE WITHOUT ID
  file.link AS Intent,
  project AS Project,
  file.mtime AS "Completed"
FROM "01-Active-Projects" OR "04-Archive"
WHERE (status = "done")
  AND file.mtime >= date(today) - dur(7 days)
SORT file.mtime DESC
LIMIT 10
```

---

*Terminal: `squirrel status` · `squirrel deadlines --level critical,urgent` · `/sq-where-am-i`*
