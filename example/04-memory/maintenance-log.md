---
type: memory
updated: 2026-09-08
---

# Maintenance log — one line per run, newest first

Rule ([the runbook](../02-processes/one-process.md), step 5): keep the 30
newest run lines; fold older ones into the counter at the bottom. Binding
budget of 60 lines, enforced by the checker. "Needs owner" items sit at the
top until a human clears them.

## Needs owner

- Nothing pending.

## Proposed compactions

- None. STATE.md has headroom; see its count in the newest run line.

## Runs

- 2026-09-08 · manual (builder session) · checker 0 FAIL / 0 WARN / 14 INFO
  -> unchanged · nothing fixed: no authorized-fix category fired. First
  readout written; BRIEFING.md and the front-desk block regenerated in the
  same action. STATE.md at 49/250 (checker-counted). Step 6 (`.bak`
  baselines) deferred to the owner's next supervised run; the nine "no .bak
  yet" INFO lines are expected until then.
- 2026-09-01 · manual (builder session) · checker 1 FAIL / 2 WARN / 9 INFO
  -> 0 FAIL / 0 WARN / 9 INFO · fixed: BRIEFING.md carried a placeholder
  date older than the ledger (regenerated); two files lacked frontmatter
  (added). One orphan, `02-processes/draft.md`, deleted after the owner
  confirmed it was scratch. No `.bak` written before the fixes (step 6 gates
  on a clean run).

…and 0 earlier runs.
