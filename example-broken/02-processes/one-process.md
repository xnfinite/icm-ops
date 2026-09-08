---
type: process
updated: 2026-09-08
---

# Run maintenance

Weekly, or whenever a session suspects drift. Takes about ten minutes. The
checker reports; this process decides what gets fixed.

## Steps

1. Run the checker from the workspace root:
   `python path/to/icm_check.py .` (it lives in the icm-maintain skill; see
   `../99-meta/README.md`). Note the summary line: N FAIL / N WARN / N INFO.
2. Fix only what is on the authorized list: missing frontmatter, a catalog
   row for a file that already exists, a dead catalog row, a broken relative
   link whose target is obvious, a ledger entry past its date (mark EXPIRED,
   never resolve it yourself), BRIEFING older than the newest readout
   (regenerate from the readout).
3. Never: delete content, resolve a decision, attach an outcome, or raise a
   budget. Those are owner judgment; write them under "Needs owner" in
   [the maintenance log](../04-memory/maintenance-log.md).
4. If a hot file is over budget, propose the compaction (what to KEEP, what
   to MOVE to a dated log file) under "Proposed compactions" and stop. Apply
   it only with the owner present.
5. Run the checker again. Append one run line to the maintenance log, newest
   first: date, trigger, before -> after counts, what was fixed. Keep the 30
   newest run lines; fold older ones into the counter at the bottom.
6. If the run ended with 0 FAIL, copy each protected file to `<file>.bak`
   (the truncation guard's baseline). Never do this after a failing run.
