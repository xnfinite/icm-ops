---
type: memory
updated: YYYY-MM-DD
---

# Advice ledger — YYYY-MM

Format and rules: the `icm-ledger` skill; grammar: `FORMAT.md` in the
icm-ops repo. Append-only; entries chronological; wrong calls stay. Ids
are `L-` / `D-` plus at least three digits, zero-padded (`L-001`),
continuous across months, never reused; numbering continues from the
previous month file (last there: L-NNN / D-NNN). The date follows
`REVIEW-BY:` / `KNOW-BY:` immediately; the settling event comes after it.
Entries marked `retro:` were reconstructed from the dated log they cite —
the one permitted exception to log-before-advising.

## L-NNN · YYYY-MM-DD · builder | advisor | <agent name>
CLAIM: the recommendation, stated so it can lose.
CONFIDENCE: low | medium | high
FALSIFIER: the observable event that would prove this wrong.
COST: cheap | hours | days | money (name it) | platform | relationship
REVIEW-BY: YYYY-MM-DD
OUTCOME: open

## D-NNN · YYYY-MM-DD · A (source): position vs B (source): position
STAKES: what is riding on it, both directions.
KNOW-BY: YYYY-MM-DD — the event that settles it.
RESOLVED: open
