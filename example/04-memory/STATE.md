---
type: memory
updated: 2026-09-08
---

# State — what is true now

Read this when the task depends on what is built, decided, or pending. Every
line here is a claim with a date; the log and the ledger hold the receipts.
Binding budget: 250 lines. Past it the checker fails the build and the fix is
compaction (`../02-processes/one-process.md`, step 4), not a bigger budget.

## What is true now

- Decision 0001 (log before advising) has been in force since 2026-08-10.
- The ledger holds six entries (L-001 to L-006) and one readout, dated
  2026-09-08. Four are resolved; two are open with review dates in December
  and January.
- The payment-retry change shipped 2026-08-14 behind a flag; the flag is
  still on. (L-001)
- The starter plan price change of 2026-08-15 is under review after the
  churn result. (L-002)
- Partner-referral calls continue at half staffing while CRM tagging is
  fixed. (L-003)
- The nightly build has run at 06:00 UTC since 2026-09-03. (L-005)
- Vendor API maintenance window: 02:00–03:00 UTC nightly
  (checked: 2026-09-08 · vendor status page · stale after: 365 days).
- Maintenance runs weekly; the latest run line is in `maintenance-log.md`.

## Open threads

- L-005 (nightly build moved to 06:00): 14 runs to observe; review by
  2026-12-31.
- L-006 (onboarding rewrite): 60-day "setup" ticket count; review by
  2027-01-31.
- CRM tagging fix for partner introductions: owner to assign.

## Open questions

- Should decision 0001 extend to disagreements between advisers (D-entries)?
  Owner's call at the 2027-09-08 review.

## Guardrails (from the 2026-09-08 readout)

- Numerals on shipping surfaces are counted before they are written (L-004).
- A "dead channel" or "price-insensitive" verdict requires one search
  outside the inherited frame (L-002, L-003).

Receipts: [the ledger](ledger/2026-09.md), [the log](log/2026-09-08.md).
