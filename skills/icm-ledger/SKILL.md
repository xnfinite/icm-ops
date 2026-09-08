---
name: icm-ledger
description: Keep score on an AI's advice inside an ICM workspace. Every consequential recommendation is logged with a confidence word, a falsifier, a cost class, and a review date BEFORE it is given; outcomes attach in the same file; readouts turn the record into a self-briefing the next session reads on arrival. Use when (1) you are about to give a recommendation that changes what the owner does next, costs money, or ships — log it first; (2) reality delivers an outcome for an open entry — attach it; (3) the owner asks "what's our track record", "where are you overconfident", or "should I trust this call"; (4) a supervised audit pass runs — compute a readout and regenerate BRIEFING.md; an unattended maintenance pass only regenerates a stale briefing from an existing readout; (5) you are about to make a call of a class the ledger scores — read your record first; (6) the owner overrides an adviser, or two advisers oppose each other — log the disagreement as a D-entry. The record is honest only if outcomes get attached.
license: MIT
metadata:
  author: "xnfinite"
  version: "0.2.0"
---

# icm-ledger

`icm-verifier` answers "was the work real?" — it scores claims about the
past. This skill answers "was the judgment good?" — it scores claims about
the future. A doctor gets outcomes; a forecaster gets scored for a lifetime;
an AI adviser produces confident recommendations at industrial volume and
never finds out whether they were right. The ledger is the fix, at the one
scale where it is honest: one operation, its advisers, their calls, and what
actually happened.

Calibration scoring is not new — forecasting communities and eval harnesses
do it. What this skill does is put the ledger *inside the working
relationship*: the AI's live recommendations carry falsifiers, outcomes
attach in the same workspace the next recommendation is made from, and the
next session reads its own record before advising again. It does not make
the adviser correct. It makes the adviser scorable, which is how you find out.

This skill operates on an ICM workspace — Interpretable Context Methodology,
Van Clief & McDermott, arXiv:2603.16021 (https://arxiv.org/abs/2603.16021).
Build the workspace with their `icm-architect` skill
(https://github.com/RinDig/icm-architect), or by hand from the paper: a
front desk (`CLAUDE.md` / `AGENTS.md`), `00-catalog/CATALOG.md`, and dated
markdown files with frontmatter — the `example/` tree in the icm-ops repo
is a complete minimal one. This pack is a layer on top of the method, not
part of it.

## First run

Create `04-memory/ledger/<YYYY-MM>.md` from `assets/ledger-month-template.md`
and number from L-001 / D-001. Add a catalog row for `04-memory/ledger/`.
Do not create BRIEFING.md before the initial readout exists; until then,
paste the no-readout block from `assets/front-desk-block.md` into
`CLAUDE.md` and `AGENTS.md`. Formats: `FORMAT.md` in the icm-ops repo
(`#ledger-entries`, `#disagreement-entries`, `#briefingmd`).

## The ledger

`04-memory/ledger/<YYYY-MM>.md` — one file per month, append-only, entries
chronological, numbering continuous across months. Never delete an entry;
wrong calls are the asset. Template: `assets/ledger-month-template.md`.
Every consequential recommendation gets:

```
## L-NNN · YYYY-MM-DD · source
CLAIM: the recommendation, stated so it can lose.
CONFIDENCE: low | medium | high   (words, never percentages)
FALSIFIER: the observable event that would prove this wrong.
COST: cheap | hours | days | money (name it) | platform | relationship
REVIEW-BY: YYYY-MM-DD             (every entry expires into review)
OUTCOME: open
```

**COST is what being wrong costs, or would have.** "The chip says 7" and
"stop working this channel" are not the same event — one costs a re-render,
the other a week. Without stakes a readout eventually rewards being right
about small things; with them it can say the sentence that matters:
"reliable most of the time, and wrong about the expensive ones."

- **Source** is the adviser: `builder` (the working session), `advisor` (a
  reviewing or parallel session), or any named agent. Owner decisions are
  not advice — they live in `01-context/decisions/`.
- **Consequential** means: changes what the owner does next, spends money or
  platform credits, ships to a client or a platform, or opens or closes a
  line of work. Routine mechanics do not get entries; the bar is "would
  anyone want to know later whether this call was right."
- **Ids** are `L-` / `D-` plus at least three digits, zero-padded
  (`L-001`), continuous across months, never reused. The date follows
  `REVIEW-BY:` (and `KNOW-BY:`) immediately; the settling event comes
  after it.
- **Log before advising, not after.** An entry written after the outcome is
  testimony, not a forecast. Seed entries reconstructed from dated logs are
  the one permitted exception — mark them with the heading suffix
  `· retro: 04-memory/log/YYYY-MM-DD.md`, the log that dates them.
- **No falsifier, no entry** — and say so in the recommendation itself: "I
  can't name what would prove this wrong" is information the owner deserves.

## Outcomes

Attach when reality shows up, with evidence at the consumption point
(`icm-verifier` drills govern disputes). **The ledger is itself a closed
loop** — everything that reads it, reads it — so any entry whose claim or
premise concerns EXTERNAL state (a platform, a client, the market) carries
an anchor outside the workspace, not a workspace citation. On 2026-08-25 one
ledger said "blocked on send" for two days while the freelance platform it
was describing showed the proposal submitted. Externally-sourced numbers in
hot files carry the stamp `checked: DATE · source · stale after: N days`;
`icm-maintain`'s checker warns when the window blows.

- `CONFIRMED` — the falsifier had its chance and did not fire.
- `CONFIRMED-IN-SCOPE` — held on what was tested; the broader claim untested.
- `DISPROVEN` — the falsifier fired. Cite the evidence.
- `MIXED` — part held, part fired; one line on which was which.
- `AVERTED` — caught wrong before it was issued or acted on. Logged because
  near-misses are the cheapest training data.
- `EXPIRED` — review-by passed with no outcome attached. An audit pass
  either resolves it or renews the date; silently stale entries are the
  ledger lying by omission.
- `MOOT` — the question dissolved before the falsifier could fire; counted
  apart from confirmed and disproven.

Amend in place — an extra line `AMENDED YYYY-MM-DD: what changed and why`,
the original lines untouched — rather than rewriting: a premise that turns
out false at creation is itself a finding (a true answer to a question
nobody asked is a closure failure, and the ledger scores those). Full
grammar: `FORMAT.md#ledger-entries` in the icm-ops repo.

## Disagreements are objects

When the owner overrides an adviser, or two advisers oppose each other on a
consequential call, the disagreement itself gets logged:

```
## D-NNN · YYYY-MM-DD · A (source): position vs B (source): position
STAKES: what is riding on it, both directions.
KNOW-BY: YYYY-MM-DD — the event that settles it.
RESOLVED: open | A | B | both-partly — evidence.
```

The owner is a player, not the referee — resolutions score both sides. Over
time the D-entries answer what no hit-rate can: **which party to trust about
which kind of question.** They also make disagreeing cheaper: a position
with somewhere to go does not have to win today, and it stops evaporating
when someone folds. Resolving a D-entry takes both parties present; an
unattended maintenance pass never resolves one and never marks it — a
KNOW-BY that has passed with RESOLVED still open is flagged for the owner
(the checker WARNs), per FORMAT.md#disagreement-entries.

## The self-briefing — how the ledger arrives instead of waiting

A record nobody opens at the moment of the mistake is décor. The correction
therefore travels to the session instead of waiting to be fetched:

- `04-memory/ledger/BRIEFING.md` — the computed briefing: each source's
  current failure class, its trigger, the replacement behavior, and the open
  items a session might resolve today. Short enough to read; receipts linked
  by entry id, not inlined. Template: `assets/briefing-template.md`.
- The front desk (`CLAUDE.md` / `AGENTS.md`, a "Know thyself" section)
  carries the two-bullet summary, so every session is briefed on arrival
  without deciding to look. Template: `assets/front-desk-block.md`.

**Regeneration duty:** whichever session writes a new readout regenerates
BRIEFING.md and the front-desk block in the same action (CLAUDE.md and
AGENTS.md are one document — edit both, identically). A briefing older than
the newest readout is a stale correction wearing a fresh voice; the checker
FAILs it.

## The readout

The point of the whole thing. Periodically, or on request, an audit pass
computes what nobody can compute without this file. Structure:
`assets/readout-template.md`. The readout is written by a supervised audit
pass; an unattended maintenance pass regenerates a stale BRIEFING.md from
an existing readout, marks expired entries EXPIRED, flags an overdue
readout under Needs owner, and never attaches an outcome or resolves a
D-entry.

- **Counts, never percentages.** "High-confidence platform-behavior calls:
  3 of 5 disproven (L-006, L-008, L-009)" — with entry ids. No cell gets a
  percentage until it holds 20+ entries; dressing n=7 as calibration
  statistics is the same sin as an unsourced market average.
- **Per source, per class.** Group each adviser's entries by the kind of
  claim (platform behavior, "this does not exist", numerals on shipping
  surfaces, market and pricing calls, what a buyer will do) and name the
  class where the failures cluster.
- **Cost-weighted sentence.** One line on where the expensive errors live
  versus the cheap ones. One operator's record found that its costliest
  entry (a week) contained zero false claims — closure, not falsehood.
- **Patterns in prose**, each backed by listed entries. Sample sizes are
  small; these are patterns with receipts, not statistics.
- The readout lives at the bottom of the month file, dated, headed
  `## Readout — YYYY-MM-DD (n=N, counts only)`, and is itself a claim — a
  later audit may revise it. Re-read the clock before writing the date;
  a session that spans days anchors "today" to a stale reading.

## Before advising, read your record

A session about to make a call of a class the ledger scores reads its record
on that class and, when the record is bad, says so in the recommendation:
"for what it's worth, calls like this have gone 1 for 4 here." That
sentence is the product: an AI whose confidence carries its own history.

If BRIEFING.md exists, it has already done this reading for you — trust it
to the `readout:` date in its frontmatter and no further.

## What this skill cannot do

- It cannot attach outcomes. A person or a session with evidence does that;
  a ledger with no outcomes is a list of opinions with dates on.
- It cannot score what was never logged. Advice given in chat and not
  entered is invisible to every readout.
- It does not make the adviser right. Read the readout as a map of where
  to check harder, not as a certificate.

Related: `icm-verifier` (the drills that settle disputed outcomes; its
pre-task briefing is the same move for execution instead of advice — an
event can appear in both its scar log and this ledger), `icm-maintain`
(expires stale entries, FAILs a stale briefing, runs the periodic pass).
