---
type: reference
updated: 2026-09-08
---

# Maintaining this workspace

This folder is about the workspace itself, not its subject. Read it when you
are changing the structure, a budget, or the checker's configuration.

## The checker

The integrity checker is `icm_check.py` from the icm-maintain skill. In a
clone of the icm-ops repo it is `skills/icm-maintain/scripts/icm_check.py`;
installed, it is `.claude/skills/icm-maintain/scripts/icm_check.py` or
`.agents/skills/icm-maintain/scripts/icm_check.py` inside a project, or
`~/.claude/skills/icm-maintain/scripts/icm_check.py` for a user. Run it from
anywhere, pointed at this root:

```
python path/to/icm_check.py .                     # human-readable, exit 1 on any FAIL
python path/to/icm_check.py . --json              # {"version", "today", "fail", "warn", "info"}
python path/to/icm_check.py . --today YYYY-MM-DD  # pins the clock: the same verdict on any day
```

It reads `icm-ops.json` at this root for budgets and folder names; every key
there is optional and the defaults are the ICM conventions. It reports and
never fixes. What may be fixed, and by whom, is in
`../02-processes/one-process.md`.

## What the checker does not see

It walks `*.md` files only. Images, PDFs and scripts are neither cataloged
nor counted by it; if they matter, catalog them by hand. It also cannot tell
whether a claim is true, only whether the file that carries it is in shape.
Of a ledger entry it reads the id, the REVIEW-BY or KNOW-BY date, the open
marker and whether the required field lines exist; it does not judge the
content of CLAIM, FALSIFIER or COST, nor whether an outcome word is one from
FORMAT.md.

## Clock-driven findings

Some findings appear with time and are the design working, not a defect:
open ledger entries past REVIEW-BY (L-005 after 2026-12-31, L-006 after
2027-01-31), decision 0001 from its 2027-09-08 review date, and the vendor
stamp in `../04-memory/STATE.md` after its 365-day window. Each is a WARN
that asks a human to resolve, renew or remove. `--today 2026-09-08` shows
the tree as it was on the day it was written.

## Adding a file

Create it with frontmatter, add its row to `../00-catalog/CATALOG.md`, run
the checker, log the change in `../04-memory/log/`.
