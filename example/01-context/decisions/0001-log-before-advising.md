---
type: decision
status: accepted
updated: 2026-08-10
review-by: 2027-09-08
---

# 0001 — Log a recommendation before giving it

## Context

Sessions in this workspace give confident recommendations at volume and never
find out whether they were right. A recommendation written down after the
outcome is testimony, not a forecast; scoring it teaches nothing.

## Decision

Every consequential recommendation (one that changes what the owner does
next, costs money, or ships) is written to `04-memory/ledger/YYYY-MM.md` with
a confidence word, a falsifier, a cost and a review date BEFORE the
recommendation is given. No falsifier, no entry, and the recommendation says
so. Outcomes attach in the same file when reality delivers them. A readout at
the bottom of the month file counts the record; the BRIEFING and the
front-desk "Know thyself" block are regenerated in the same action.

## Consequences

- Recommendations get slower by one paragraph and become checkable.
- Wrong calls stay in the file; they are the asset.
- Review on 2027-09-08: keep if at least two readouts changed a session's
  behavior in a way the log can show; otherwise reduce to money-only calls.
