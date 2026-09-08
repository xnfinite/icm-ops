---
type: memory
updated: YYYY-MM-DD
---

# Maintenance log — one line per run, newest first

Rule (the `icm-maintain` skill): one physical line per run where possible,
detail in the daily log; keep as many run lines as fit under the budget
(60 by default, binding in the checker); fold the rest into the counter at
the bottom. "Needs owner" items sit at the top until a person clears them.
This file needs a catalog row; the default `hot_budgets` in `icm-ops.json`
already names it.

## Needs owner

- Nothing pending.

## Proposed compactions

- None.

## Runs

- YYYY-MM-DD · <trigger: scheduled | manual | session-start hook> · checker
  N FAIL / N WARN / N INFO -> N FAIL / N WARN / N INFO · fixed: <what, from
  the authorized list; or "nothing"> · <hot file> at N/N (checker-counted).

…and 0 earlier runs.
