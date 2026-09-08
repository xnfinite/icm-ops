---
name: icm-maintain
description: Keep an ICM workspace structurally true across sessions — a read-only integrity checker (catalog rows, orphan files, broken links, frontmatter, binding line budgets on hot files, decision review-by clocks, expired ledger entries, stale briefing, stale external-number stamps, date drift, truncation against .bak copies), a bounded maintenance run with an explicit "authorized to fix" list and a "never" list, a five-minute compaction routine for over-budget hot files, and a budgeted maintenance log. Use when (1) starting or ending a session in an ICM workspace ("run the check", "is the workspace clean"); (2) a scheduled or unattended maintenance session runs; (3) the checker FAILs a hot-file budget and something must be compacted; (4) a file was just written and may have been truncated; (5) the owner asks "what needs me", "what drifted", or "why is the catalog out of date"; or (6) setting per-workspace budgets and protected files in icm-ops.json. Detects and stages; a person applies the subtractive fixes.
license: MIT
metadata:
  author: "xnfinite"
  version: "0.1.0"
---

# icm-maintain

A context workspace decays under use: hot files regrow, catalog rows point
at moved files, a review date passes and nobody notices, a ledger entry
expires in silence, a briefing goes stale while still sounding current.
This skill is the routine that keeps that from compounding — mechanical
first, judgment second, and never more authority than an unattended session
can be trusted with. The system should not wait for someone to remember it.

This skill operates on an ICM workspace — Interpretable Context Methodology,
Van Clief & McDermott, arXiv:2603.16021 (https://arxiv.org/abs/2603.16021).
Build the workspace with their `icm-architect` skill
(https://github.com/RinDig/icm-architect); this pack is a layer on top of
the method, not part of it.

## The checker

```
python skills/icm-maintain/scripts/icm_check.py <workspace-root>
python skills/icm-maintain/scripts/icm_check.py <workspace-root> --json
```

Exit `0` = no FAIL findings; `1` = at least one FAIL; `2` = configuration
error (bad `icm-ops.json`, missing catalog). `--json` emits the findings as
machine-readable output for a test or a hook. The checker is **read-only:
it reports and never fixes.** Its report is the worklist. It covers:

| Finding | Level | What it means |
|---|---|---|
| Catalog row points at a missing path | FAIL | The map lies. |
| Markdown file with no catalog coverage | WARN | Invisible to every session. |
| Relative link does not resolve | FAIL | A pointer to nowhere. |
| Missing frontmatter | WARN | Type and date unknown. |
| Hot file over its **binding budget** | FAIL | Compaction is due (below). |
| Other file over the size target | WARN / FAIL | Doing two jobs; historical records WARN, working files FAIL. |
| Decision without `review-by:` / past it | WARN | Owner call needed. |
| Ledger L/D entry past REVIEW-BY or KNOW-BY and still open | WARN | Resolve or mark EXPIRED. |
| `BRIEFING.md` older than the newest readout | FAIL | A stale correction wearing a fresh voice. |
| `checked: DATE · source · stale after: N days` window blown | WARN | An external number describing the past as the present. |
| Newest log dated in the future | FAIL | A date written from a wrong clock. |
| Protected file below 40% of its `.bak` | FAIL | Possible truncation — recover, do not overwrite the `.bak`. |

The report's opening line prints today's date and the newest log's age.
Dates are claims; that line is the clock.

Budgets are FAILs, not WARNs, by design: a WARN that stays yellow for weeks
becomes wallpaper. One operator measured the decay — a state file regrew
from 232 to 273 lines in the seven days after a trim, with WARNs firing the
whole time. Binding budgets plus a five-minute routine held it after that.
The checker owns the line-count definition (`wc -l` semantics) because it
is the tool that fails the build; an off-by-one at a binding threshold is
real.

## Configuration — `icm-ops.json` at the workspace root (optional)

Defaults are the ICM conventions. Override per workspace with any subset:

| Key | One line |
|---|---|
| `hot_budgets` | Map of path → max lines that FAIL when exceeded. Default: `04-memory/STATE.md` 250, `00-catalog/CATALOG.md` 155, `04-memory/maintenance-log.md` 60. |
| `protected` | Paths that get a `.bak` after a clean run and a truncation FAIL if they collapse. Default: front desk, CATALOG, CONVENTIONS, STATE, BRIEFING, maintenance-log, plus the newest ledger month and newest log. |
| `deliverable_markers` | Path substrings marking client-facing content inside artifacts; exempt from orphan and frontmatter checks (their parent row covers them). Default: `/product/`, `/sample/`, `/example/`. |
| `frontmatter_exempt` | Root-level files that need no frontmatter. Default: `CLAUDE.md`, `AGENTS.md`, `README.md`. |
| `size_target_lines` | Soft size target; over it WARNs, over twice it FAILs (working files) or WARNs (historical). Default: 200. |
| `historical_dirs` | Directories whose files are records, not working files — oversize is a WARN there. Default: `04-memory/log/`, plus ledger month files. |
| `ledger_dir` | Where month files, readouts, and `BRIEFING.md` live. Default: `04-memory/ledger/`. |
| `decisions_dir` | Where numbered decision records with `review-by:` live. Default: `01-context/decisions/`. |
| `catalog` | The map the coverage and row checks read. Default: `00-catalog/CATALOG.md`. |

Raising a budget is an owner call, recorded with a reason in the workspace.
A budget raised to dodge a compaction is the wallpaper failure wearing a
number.

## Run maintenance — the workspace fixes its own errors, within limits

A scheduled session runs this daily; any session may run it on demand.
About fifteen minutes.

1. Run the checker. The report is the worklist.
2. **Authorized to fix without asking** — additive or reversible ONLY;
   nothing on this list can lose information:
   - Hot file over budget → **detect and STAGE, never apply.** Write the
     proposed keep/move diff to `04-memory/maintenance-log.md` under
     "Proposed compaction," and stop. Compaction is the one subtractive
     operation in the system and it takes the keep/move judgment; an
     unattended session that cuts a live guardrail produces a green check
     that the next unattended run trusts — the producer declaring itself
     verified, daily, forever. A person or a supervised session applies it.
   - Missing frontmatter → add it (type by folder, `updated:` from the
     file's mtime).
   - Catalog row pointing at a missing file → remove the row. Orphan file →
     add a row if its purpose is evident from the file itself; else list it
     for the owner.
   - Broken relative link → repair if the target is findable by name
     search; else report.
   - Ledger entry past its date, still open → attach the outcome if
     evidence exists in the logs; else mark `EXPIRED` per `icm-ledger` and
     renew or retire the date.
   - Decision past `review-by:` → do NOT reopen it; add one line flagging it
     for the owner and renew nothing.
   - Stale `BRIEFING.md` (FAIL) → regenerate it AND the front-desk block
     from the newest readout, per `icm-ledger`.
3. **Never**: raise budgets, delete files, edit money surfaces (listings,
   proposals, anything a client or a platform reads), publish anything,
   resolve D-entries (both parties present for that), or edit decisions.
   Judgment stays with sessions the owner is driving. A maintenance session
   that improvises is worse than one that waits.
4. Re-run the checker. It must end 0 FAIL — except a hot-file budget FAIL,
   which ends as a staged proposal awaiting a human.
5. **Back up the protected files — ONLY after the checker is clean.** Copy
   each protected file to `<file>.bak` (last-known-good). Order matters:
   if the checker raised a POSSIBLE TRUNCATION FAIL, do not back up —
   recover the file from its existing `.bak`, then re-run. Never refresh a
   `.bak` from a file the checker flagged.
6. **Log to `04-memory/maintenance-log.md`, not the daily log** — one line
   per run, newest first. Anything needing a human goes under "Needs owner"
   at the top of the same file, where it sits until a person clears it.

**The maintenance-log rule.** The file keeps the 30 newest run lines; when
over, fold the oldest into the single "…and N earlier runs, all green"
counter at the bottom. It carries a binding budget (60 lines by default)
in the checker. **The immune system must not become the disease**: 365
daily lines in a budget-enforced workspace would make the bloat-watcher
the biggest source of bloat.

## Compact the hot files — five minutes, whenever the checker says so

The point is making shrinkage ordinary: a trim that is a project happens
once a quarter; a trim that is a chore happens when the checker says so.

1. Run the checker. Note which hot file is over budget and by how much.
2. Read the on-disk file before anything else — never compact from memory
   of it.
3. Apply the one test to the oldest and fattest sections: **"if a session
   never read this line, would it do something wrong?"**
   - KEEP: corrections that overturn wrong beliefs, prohibitions and
     guardrails, open threads, next actions, live deadlines, pointers.
   - SHRINK: any recently-changed entry older than about seven days
     collapses to its headline plus a pointer to the log that owns the
     story.
   - MOVE what already has an owner, and nothing else. Before cutting a
     line, verify its content exists at the owner — whitespace-normalized
     check, not naive substring (the wrapped-phrase scar in
     `icm-verifier`). If it has no owner, it stays or gets one. Nothing is
     ever deleted to nowhere.
4. Edit section by section; never regenerate the whole file. Update the
   `updated:` frontmatter from the CLOCK, not the session's memory of the
   date. A correction must replace the stale line, not merely follow it —
   an appended correction leaves the lie standing upstream of the truth.
5. Re-run the checker; confirm the FAIL cleared. One line in today's log:
   what moved, where its owners are, before and after line counts.

## Writing files safely — the rule the truncation guard exists for

- Write atomically: temp file, then replace. Never overwrite a file with a
  single failable write; the failure mode is total, not partial.
- Always UTF-8. A default-codepage write dies on `→ · —` and takes the file
  with it.
- Prefer append and edit tooling over read-then-rewrite round trips.
- A suspiciously small file right after a write is a data-loss signal, not
  a relief. Read it back.

## What this skill does not do

It does not judge content. A file can be perfectly cataloged, linked,
budgeted, dated, and wrong; that is `icm-verifier`'s job for claims about
work and `icm-ledger`'s for claims about the future. It does not enforce
anything on an agent that does not run it — wire it into a session start,
a scheduled run, or a hook, and read the "Needs owner" section when it
tells you to.
