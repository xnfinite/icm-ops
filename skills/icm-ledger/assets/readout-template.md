# Readout structure

Append to the bottom of the current `04-memory/ledger/<YYYY-MM>.md`. Date
it from the clock, not from memory. Counts with entry ids, never
percentages below n=20. Then regenerate `BRIEFING.md` and the front-desk
block in the same action — a readout without a regenerated briefing is a
correction nobody will receive.

```
## Readout — YYYY-MM-DD (n=N, counts only)

- **<source>, N entries:** N confirmed (L-…), N confirmed-in-scope (L-…),
  N disproven (L-…), N mixed (L-…), N averted (L-…), N expired (L-…),
  N moot (L-…), N open. Failure class: <one sentence naming the kind of claim the
  disproven entries share, e.g. "numerals on shipping surfaces asserted
  without the check that was one step away">. Where it was reliable:
  <the kind of claim the confirmed entries share, e.g. "verdicts backed
  by a probe it ran">.
- **<source>, N entries:** … (one bullet per adviser that has entries)
- **Cost-weighted sentence:** which errors were cheap and caught fast;
  which were expensive and why the drills did not catch them. Name the
  entry ids. This is the line the owner reads if they read nothing else.
- **D-entries:** N open, N resolved for A, N for B, N both-partly. Which
  party has been right about which kind of question, with ids.
- **Corrections to earlier readouts:** if this pass revises a prior
  readout's pattern, say what changed and cite the entries that moved it.
- **Open items a session might resolve today:** entry ids with their
  KNOW-BY / REVIEW-BY dates.
- Sample sizes are small; these are patterns with receipts, not
  statistics. Next readout when: <the event or date>.
```

`MOOT` is counted apart from confirmed and disproven: the question
dissolved before the falsifier could fire, so the entry scores neither
way. An entry with no `OUTCOME:` line counts as open and gets flagged in
the readout by id.

## COST classes — what being wrong would have cost

| Class | Meaning | Verification owed (per `icm-verifier` calibration) |
|---|---|---|
| `cheap` | Reversible in minutes; internal; nobody outside the workspace sees it. | Report and move on; "done, unverified" may stand. |
| `hours` | A re-render, a rewrite, a lost working block. | One read-back at the point that would fail loudest. |
| `days` | A lost week of a lane; a build on a wrong premise. | Full consumption-point pass before acting on it. |
| `money (name it)` | A spend, a fee, a lost sale — write the figure or the range. | Full pass, every time. |
| `platform` | Standing with a marketplace, a store, a host: listing health, account rules, ranking. | Full pass; anchor outside the workspace. |
| `relationship` | Trust with a client, a collaborator, a community. | Full pass; a wrong public number costs more than a wrong private one. |

A readout groups disproven entries by COST as well as by class. "Reliable
most of the time, and wrong about the expensive ones" is a sentence a
count-only readout can say; a hit-rate cannot.
