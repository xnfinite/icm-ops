---
type: reference
updated: 2026-09-08
---

# Maintaining this workspace

This folder is about the workspace itself, not its subject. Read it when you
are changing the structure, a budget, or the checker's configuration.

## The checker

The integrity checker is `icm_check.py` from the icm-maintain skill
(`skills/icm-maintain/scripts/icm_check.py` in the icm-ops repo, or wherever
that skill is installed). Run it from anywhere, pointed at this root:

```
python path/to/icm_check.py .            # human-readable, exit 1 on any FAIL
python path/to/icm_check.py . --json     # {"fail": [...], "warn": [...], "info": [...]}
```

It reads `icm-ops.json` at this root for budgets and folder names; every key
there is optional and the defaults are the ICM conventions. It reports and
never fixes. What may be fixed, and by whom, is in
`../02-processes/one-process.md`.

## What the checker does not see

It walks `*.md` files only. Images, PDFs and scripts are neither cataloged
nor counted by it; if they matter, catalog them by hand. It also cannot tell
whether a claim is true, only whether the file that carries it is in shape.

## Clock-driven findings

Some findings appear with time and are the design working, not a defect:
open ledger entries past REVIEW-BY (L-005 after 2026-12-31, L-006 after
2027-01-31), decision 0001 after its 2027-09-08 review date, and the vendor
stamp in `../04-memory/STATE.md` after its 365-day window. Each is a WARN
that asks a human to resolve, renew or remove.

## Adding a file

Create it with frontmatter, add its row to `../00-catalog/CATALOG.md`, run
the checker, log the change in `../04-memory/log/`.
