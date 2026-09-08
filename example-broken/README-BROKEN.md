---
type: reference
updated: 2026-09-08
---

# example-broken — five seeded defects

This tree is `../example/` with five defects added on purpose. The checker
must name every one; `scripts/test.py` asserts that it does. Nothing else
differs, so any other finding is a bug in the checker or drift in the copy.

| # | Defect | Where | Expected finding |
|---|---|---|---|
| 1 | Hot file over its binding budget: STATE.md padded past 250 lines with a "Backlog" section of routine notes | `04-memory/STATE.md` | FAIL: `04-memory/STATE.md: N lines — OVER its binding budget of 250` |
| 2 | Uncataloged file: a process with valid frontmatter and no catalog row | `02-processes/orphan.md` | WARN: `no catalog coverage ... 02-processes/orphan.md` |
| 3 | Broken relative link: the receipts line links to a runbook that does not exist | `04-memory/STATE.md`, last paragraph before the padding | FAIL: `broken relative link in 04-memory/STATE.md: (../02-processes/does-not-exist.md)` |
| 4 | Ledger entry past its date and still open: L-003 has `REVIEW-BY: 2026-08-01` and `OUTCOME: open` | `04-memory/ledger/2026-09.md` | WARN: `ledger L-003 past its date (2026-08-01) and still open` |
| 5 | Stale briefing: BRIEFING.md is dated 2026-08-01, the newest readout 2026-09-08 | `04-memory/ledger/BRIEFING.md` | FAIL: `BRIEFING.md (2026-08-01) is OLDER than the newest ledger readout (2026-09-08)` |

Severities are the original checker's: an over-budget hot file, a broken link
and a stale briefing fail the build; an orphan and an expired ledger entry
warn, because both need a human to decide (catalog it or delete it; resolve
it or mark it EXPIRED). Expected summary line: `3 FAIL / 2 WARN / 13 INFO` (one INFO fewer
than `example/`, because STATE.md's budget line is now the FAIL).

Two things are left deliberately inconsistent, because the checker reads
structure, not prose: the readout at the bottom of the ledger still counts
L-003 as "mixed", and the front desk still cites the 2026-09-08 readout that
the stale BRIEFING never absorbed. That gap is the defect.

Run: `python skills/icm-maintain/scripts/icm_check.py example-broken` from the
icm-ops repo root. Exit code 1.
