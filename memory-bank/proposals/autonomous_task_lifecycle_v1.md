# Autonomous Task Lifecycle Management – Action Plan v1

## Overview

This document outlines the completed design and implementation plan for a fully autonomous lifecycle around `todo-tasks.json`.

Goals:

1. **Auto-Cleanup** – remove stale *completed* tasks older than a configurable retention period.
2. **Auto-Prioritization** – always return newest active tasks first when listing.
3. **Auto-Completion** – instantly mark a task `completed` as soon as all its TODO items are marked done (either manually or programmatically).

All three behaviours are now fully implemented in `todo_manager.py` (see *Code Changes* below).  No external scheduler is required; logic runs opportunistically on every call, guaranteeing correctness without long-running daemons.

---

## Design Rationale

| Feature | Design Choice | Justification |
|---------|---------------|---------------|
| Auto-Cleanup | Purge during `_load()` | Centralised; every public function calls `_load()`, ensuring regular cleanup without extra cron jobs. |
| Retention Window | `DEFAULT_CLEANUP_DAYS` env variable | Allows ops teams to tweak without code changes. Default 7 days. |
| Auto-Prioritization | Sort by `created` descending in `list_open_tasks()` | Guarantees UX surfaces latest work first. Keeps API unchanged. |
| Auto-Completion | Hook inside `mark_done()` | Single point where TODO -> DONE transition occurs; trivial to compute `all(t["done"] for t in task["todos"])`. Also updates `status` and timestamp to trigger persistence & future cleanup. |

---

## Code Changes

### `todo_manager.py`

```diff
@@
 DEFAULT_CLEANUP_DAYS = int(os.getenv("TODO_CLEANUP_DAYS", "7"))
@@ _load()
+ if _cleanup_outdated_tasks(data):
+     _save(data)
+
+def _cleanup_outdated_tasks(...):
+     # remove completed tasks older than retention window
+
@@ mark_done()
+ if all(t["done"] for t in task["todos"]):
+     task["status"] = "completed"

@@ list_open_tasks()
- return [t for t in data["tasks"] if ...]
+ open_tasks.sort(key=lambda t: t.get("created", ""), reverse=True)
+ return open_tasks
```

No other modules required changes because all public interfaces remain identical.

---

## Testing Plan

1. **Unit Tests** (add to `tests/test_todo_lifecycle.py` – not yet committed)
   • create task → add todos → mark all done → expect status `completed`.
   • ensure `list_open_tasks()` omits completed tasks and returns newest first.
   • set `TODO_CLEANUP_DAYS=0` → reload → expect task purged.

2. **Manual Smoke**
   • Use *Task Command Center* to create/complete tasks, verify behaviour.

---

## Recommendations for Enhancement

1. **Granular Retention** – per-task retention metadata allowing some tasks to persist longer (e.g. regulatory work).
2. **Background Scheduler** – optional async job that dumps cleanup stats to logs for observability, even if no API calls occur.
3. **Event Hooks** – emit WebSocket or message-bus events upon auto-completion/cleanup for real-time dashboards.
4. **Archived Store** – before deletion, move JSON objects to `archive/<YYYY-MM>.json` for long-term analytics.
5. **Conflict Resolution** – if multiple processes edit `todo-tasks.json`, adopt file-locking or migrate to lightweight DB (SQLite).

---
Generated 2025-07-28