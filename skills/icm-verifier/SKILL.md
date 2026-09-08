---
name: icm-verifier
description: Verify that claimed work is real before reporting, shipping, or building on it — a work-truth discipline for AI sessions that sometimes report work they did not do. One law (a claim is not reportable until observed at the point where it will be consumed), eight faces the false "done" wears, a drill per face, a report grammar, and an audit mode. Use when (1) you are about to report any multi-step work as done; (2) auditing another session's or agent's report of its own work ("did it actually happen", "audit this", "verify the report"); (3) a deliverable is about to ship to a client, a marketplace, or a platform; (4) a check or sweep returned a suspiciously clean or suspiciously short result; (5) reconciling work from parallel sessions on one workspace; (6) a number, a "does not exist", or a "this channel is dead" is about to be stated; or (7) the user says "trust check", "verify this", "is that actually true", or pastes another AI's summary of its own work. Makes claims checkable, not the agent correct.
license: MIT
metadata:
  author: "xnfinite"
  version: "0.2.0"
---

# icm-verifier

An AI will sometimes tell you work is done when it is not. Not from malice —
from summarizing intent instead of observing outcome. Every rule in this
skill exists because that happened in one operator's workspace and the error
survived at least one review. The catches are kept in a scar log
(`references/scar-log-template.md` shows the format with anonymized
examples); this file is the drill.

**The one law: a claim is not reportable until verified by observation at
the point where it will be consumed.** Not where it was made — where it will
be read, rendered, downloaded, or executed.

This skill operates on an ICM workspace — Interpretable Context Methodology,
Van Clief & McDermott, arXiv:2603.16021 (https://arxiv.org/abs/2603.16021).
Build the workspace with their `icm-architect` skill
(https://github.com/RinDig/icm-architect), or by hand from the paper: a
front desk (`CLAUDE.md` / `AGENTS.md`), `00-catalog/CATALOG.md`, and dated
markdown files with frontmatter — the `example/` tree in the icm-ops repo
is a complete minimal one. This pack is a layer on top of the method, not
part of it. It does not make an agent correct. It makes the agent's claims
checkable, and the checks visible.

## The eight faces of the same lie

The false "done" wears predictable disguises. Learn them by face.

1. **Container work.** Work done inside a chat, tool, or session container
   that never landed on disk. The session describes files in loving detail;
   the filesystem has never heard of them.
2. **The short-circuited check.** A `check && act` chain fails silently at
   its opening link, and the fallback prints a clean-looking result from a
   check that never ran. The report is fiction with good formatting.
3. **Verified in the wrong place.** Right artifact, wrong size, crop,
   format, or copy. A clipped line at thumbnail size looks like a normal
   line at canvas size; a fix in the repository is not in the file the
   client downloads from the platform. "In the product" means in the thing
   the consumer receives, at the moment they receive it.
4. **The false negative.** "The file doesn't exist" after searching one
   guessed directory; "no matches" from a substring check that is blind to
   a letterspaced wordmark, a line-wrapped phrase, or text baked into an
   image; "not in the list" from a tool whose own description says what it
   does not list. Absence is a claim like any other, and it needs the
   catalog, a whole-tree search, the normalized forms, and the instrument's
   stated coverage before it may be spoken.
5. **The number read as a label.** A count on a surface ("7 folders")
   parsed as decoration by every reviewer while the panel beside it shows
   eight rows. Its nastier variant is the agreeable number: a figure that
   survives because the conclusion it supports is right — nobody audits the
   arithmetic on a claim they are nodding along to, even when the
   contradicting figure sits in their own pasted output. Numerals are
   claims about the world; count them against their referents.
6. **Self-reported verification.** "Verified correct" written by the same
   process that did the work, without naming the observation that would
   have failed if it were wrong. Verification that cannot say what it
   looked at is a mood, not a check. "It's on a timer" reported before any
   timer had fired is this face wearing a clock.
7. **Premature closure.** True premises, wrong conclusion. Nine honest
   searches, every negative correctly verified — and the market sat under
   the words a buyer would use, not the words the searcher would. Every
   step checks green because the error lives in the frame the steps
   inherited. The one face where rigor itself builds the confidence in the
   wrong answer; it cost a week.
8. **The closed loop.** The check shares its source with the claim it
   checks. A page priced FROM the engine agrees with the engine forever —
   green means self-consistent, not correct; if the rate card is wrong
   against the shop's real prices, every surface and every drill still
   agree, and all of it is wrong. Found by red-team on 2026-08-25, before
   it cost anything. Independence of METHOD is not independence of SOURCE.

## The drills

Run the ones the situation calls for. Each drill defeats specific faces.

**Read-back drill** (faces 1, 2 — after every write you intend to report):
read or grep the written content back *from the target file*, and confirm
the expected occurrence count. Never guard a write with `&&` on an
unverified path. "Edit succeeded" is not proof of count — a `replace_all`
can under-match silently.

**Watched-check drill** (faces 2, 6): **a suite you did not watch run did
not run.** Run checks as standalone commands with visible output; a chained
sweep that prints one tidy line gets rerun unchained. Suspiciously short
output is a rerun trigger, not a relief — a suspiciously small file right
after a write is a data-loss signal, not a success.

**Consumption-point drill** (face 3): verify at the exact size, crop,
format, and location of consumption. Covers: at thumbnail AND the grid's
crop of the thumbnail AND full size. PDFs: rendered pixels, not source
HTML. Archives: extracted from the shipped file, not the staging folder.
Listings: the platform's live copy, not the repo.

**Negative drill** (face 4): before reporting anything missing, get its
expected path from `00-catalog/CATALOG.md`, then search the whole workspace
by name — and by the whitespace-normalized and letterspaced forms when the
target is text, and by rendered pixels when it may be inside an image.
Tools count as search scopes: read what the tool says it does NOT cover
before reporting absence from its output. A negative names its instrument,
that instrument's stated coverage, and its mounts. Report "not found at its
cataloged path or by name-search" — never "does not exist."

**Count drill** (face 5): every numeral on a shipping surface gets counted
against the thing it counts, at review time, every time. If the referents
are visible in the same artifact, count them there. Run it HARDEST on
numbers attached to conclusions you agree with — agreement feels like
verification, and that is the whole trick.

**Landing drill** (faces 1, 6 — after any parallel session, agent, or
external tool reports work): list the workspace's files by modification
time and diff claimed-against-landed before acting on the report. A
transcript describing renders is a spec, not a deliverable, until the files
exist. Two sessions on one workspace reconcile through the filesystem,
never through each other's summaries.

**Independent-recheck drill** (face 6): verify with a method the producer
did not use. A self-asserting packer still gets its archive listed by a
separate command; a generator's "rendered OK" still gets its output opened;
"scheduled" means created, persisted, AND observed to fire once. The
producer's own success message is testimony, not evidence.

**Reframe drill** (face 7 — before declaring anything absent, dead, or
exhausted): name the assumption your search inherited from how you framed
the question, then run ONE search that deliberately abandons it. The
canonical form: "I have been searching what I call it — what would a buyer
call it?" A closure without a reframe pass is a guess wearing
verification's clothes.

**Outside-anchor drill** (face 8 — for any self-consistent system): at
least one number gets checked against a source OUTSIDE the loop that
generated it — the client's actual invoice, the platform's live page, the
physical world. Internal consistency proves the pipes, not the water.

## Pre-task briefing — before the work, not after

The scar log teaches after the fact; this section turns it around. Before
starting work of a class that has scarred before — rendering and checking
visuals, packaging archives, sweeping text for presence or absence,
shipping copy with numerals, reporting on state another session claims —
open the scar log, pull the entries for THIS class of work, and say in the
session, before any artifact is made, which faces the task risks and which
drill catches each. Not "verify your claims" — "you are about to verify
PDFs by string sweep: that false-negatived twice (a letterspaced notice, a
wrapped phrase); the catch is rendered pixels plus the whitespace-normalized
form." A named risk with a named check changes behavior; generic vigilance
is noise. If the advice ledger (`04-memory/ledger/`, the `icm-ledger`
skill) scores your record on this class of call, read that too — arriving
already knowing how you tend to fail is the point.

## Calibration — verification scales to stakes

The drills say "check"; this section says how much. Uniform rigor is
miscalibrated in both directions at once: an agent that checks everything
is not safe, just slow instead of wrong, and it spends the attention of the
person it serves. Scale by the ledger's COST vocabulary:

- **Cheap, reversible, internal** → report and move on. "Done, unverified"
  is a complete, honest, and PERMANENT answer here.
- **Hours or days at stake, or awkward to reverse** → one read-back at the
  point that would fail loudest, then move.
- **Money, platform, relationship — public or irreversible** → the full
  consumption-point discipline, every time, no exceptions.

The founding week of this discipline produced both errors: unverified
numerals on shipping surfaces AND repeated re-verification of byte-identical
installed copies. Over-checking is spending someone else's time to purchase
confidence nobody asked for.

Why the drills are shaped this way, and how a new face gets designed
before it costs anything: `references/design-notes.md`.

## Report grammar

Every completion report states its evidence or its absence:

- **"Done — verified by [observation]"** where the observation names what
  was looked at and what would have failed if wrong. ("Verified by reading
  the chip text back from the re-rendered PNG at full size.")
- **"Done, unverified"** when verification has not run yet — acceptable
  mid-work, never at ship.
- **"Created, firing untested"** for anything scheduled that has not been
  observed to fire.
- Never a bare "done." Never "verified" without the observation.
- Negatives carry their search scope and instrument: "zero matches across
  all 44 files, case-insensitive, whitespace-normalized; the tool does not
  index images."
- Capability claims name their failure modes — the grammar applies to sales
  copy too.

## Audit mode

When handed another session's (or your own earlier) report:

1. Extract every claim — each "done," each number, each "verified," each
   "doesn't exist," each date.
2. For each, ask: what observation would prove this at the consumption
   point? Has anyone made it?
3. Run the landing drill first (is the work even on disk?), then the
   cheapest disproving check per claim.
4. Report claim-by-claim: confirmed-by-observation / disproven / untested.
   An untested claim stays labeled untested — do not round it up to true.
   The evidence check applies to every report, including the owner's.

## Keeping the scar log

Every catch gets one dated line in the scar log, with the face it wore, how
it was caught, and the rule it produced or confirmed. Newest first. The log
lives at a workspace path with a catalog row —
`02-processes/icm-verifier/scar-log.md` unless the catalog says otherwise —
never inside an installed skill folder (`.claude/skills/`,
`.agents/skills/`): a file there sits outside the checker's walk and is
overwritten by the next reinstall. Format:
`references/scar-log-template.md`. The log is the evidence the discipline
is lived, not aspirational — and the raw material for the pre-task
briefing.

The measure of this skill working: catches move earlier. A count caught at
review costs a re-render; caught at publish, a listing; caught by a buyer,
the product's reputation; caught by tooling before a person sees it, nothing.
