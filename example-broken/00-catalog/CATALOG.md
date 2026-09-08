---
type: catalog
updated: 2026-09-08
---

# Catalog

Entries say what a file is *for* and when to read it, never what it contains.
Keep this file under ~150 lines; the checker enforces a binding budget of 155.

| File | Read when |
|---|---|
| `CLAUDE.md` / `AGENTS.md` | Always, first. Identical files; either one works. |
| `00-catalog/CATALOG.md` | Always, second. This file. |
| `00-catalog/CONVENTIONS.md` | Before your first write in a session. |
| `01-context/decisions/0001-log-before-advising.md` | You wonder why recommendations get logged before they are given. |
| `02-processes/one-process.md` | You are running maintenance: the checker, the authorized fixes, the run line. |
| `04-memory/STATE.md` | Always, if the task depends on what is true now. |
| `04-memory/log/` | You need history. One file per day on which something material happened. |
| `04-memory/log/2026-09-08.md` | The day the readout was written. |
| `04-memory/ledger/2026-09.md` | You are about to give a consequential recommendation, or an outcome has landed. |
| `04-memory/ledger/BRIEFING.md` | You arrived and want the full version of the Know-thyself block. |
| `04-memory/maintenance-log.md` | You are checking when maintenance last ran and what it found. |
| `99-meta/README.md` | You are changing the workspace itself, or running the checker. |
| `README-BROKEN.md` | You want the list of the five seeded defects and the finding each produces. |
| `icm-ops.json` | You are changing a file budget or a folder name the checker reads. |

Before concluding a file is missing, check this catalog, then search by name.
