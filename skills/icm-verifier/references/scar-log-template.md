---
type: reference
updated: YYYY-MM-DD
---

# Scar log — every catch that produced or confirmed a rule

Copy this file to your workspace (the catalog decides where; a common home
is `02-processes/icm-verifier/scar-log.md` or the skill's own
`references/scar-log.md`) and replace the examples with your own catches.
Keep the format. Newest first. This file is the proof the discipline is
lived; it is also what the pre-task briefing reads.

## Entry format

```
## YYYY-MM-DD — one-line title naming the face

- **What was claimed.** What was true. How it was caught (by whom, with
  what observation). Face N (name). Rule produced or confirmed: <one
  sentence, and where it now lives if it became a convention or a check>.
```

One bullet per catch; several catches on one day share a heading. Cite the
ledger entry (`L-NNN`) when the same event is also a judgment failure — an
event can appear in both books.

## Example scars — six from one operator's record, anonymized

The dates are real. Platforms, products, and figures are made generic;
the shape of each failure is untouched, because the shape is the lesson.

## 2026-08-25 — the closed loop catches the ledger itself, within the hour

- **The accountability system carried a false belief about its own most
  consequential entry for two days.** A ledger entry said "blocked on
  send; proposals parked" while the freelance platform it described showed
  the proposal submitted two days earlier. Nothing inside could see it:
  everything that reads the ledger reads the ledger — the workspace
  agreeing with itself about the world. Caught by the owner opening the
  platform directly, fifteen minutes after face 8 was named in a red-team
  exercise. Cascade: a second entry urged a send that had already
  happened, and a disagreement entry argued about a choice already made.
  Face 8 (closed loop). Rules: any ledger entry about external state
  carries an anchor outside the workspace, not a workspace citation; and
  externally-sourced numbers in hot files carry
  `checked: DATE · source · stale after: N days`, enforced by the checker.
- **Premature closure, diagnosed from the ledger's most expensive entry.**
  Nine searches on the platform, every one honestly run, every negative
  correctly verified, conclusion "this channel is dead" — wrong, cost a
  week; the market sat under buyer vocabulary while every search used the
  searcher's. No existing drill could catch it because nothing was false
  except the synthesis. Face 7. Produced the reframe drill: name the
  inherited framing, run one search that abandons it.

## 2026-08-25 — absence reported past the instrument, and the agreeable number

- **"The timer isn't there."** A reviewing session declared two scheduled
  tasks nonexistent after querying a registry that, by its own tool
  description, does not list locally stored tasks. The tasks existed on
  disk in the other registry, enabled, with a next-run time. The
  instrument documented its blind spot; the limitation was quoted back as
  a discovery. Face 4 (false negative). Rule: a negative names its
  instrument AND the instrument's stated coverage. Same day, the other
  direction: "it's on a timer" was reported before any timer had fired —
  face 6; "scheduled" now means created, persisted, and observed to fire
  once, and the grammar until then is "created, firing untested."
- **"The state file regrew to its pre-trim size in one week."** Shipped in
  an audit whose own pasted checker output held the contradicting figures
  (the regrowth was about a quarter of the cut, not all of it). The
  conclusion the number supported was right — decay is real, detectors do
  not shrink anything, budgets should bind — and the builder built on it
  within the hour without checking the arithmetic either. Agreement
  suppressed the check on both sides. Face 5, the agreeable variant.
  Rule: the count drill runs hardest on numbers you are nodding along
  to. Also caught the same hour: the audit's line counts mixed two
  definitions (wc-style versus newline-plus-one); at a binding threshold
  with two lines of headroom, off-by-one is real. The checker now owns
  the definition, because it is the tool that fails the build.

## 2026-08-25 — the date scar recurs, caught by machine

- **Tuesday's work written under Sunday's date.** A session spanning three
  calendar days anchored "today" to a clock reading taken on day one; the
  ledger, the self-briefing, the front-desk block, and a readout all
  shipped dated two days early. Caught by the checker's own mtime
  stamping — the earliest scar in this record caught by tooling rather
  than a person, which is the skill's own success metric (the catch moved
  earlier). Face 5 cousin: a date is a claim. Rule: in a long-running
  session a prior clock reading is not "now" — re-read the clock before
  writing any date; the checker prints today's date and the newest log's
  age at the top of every report so drift is visible on every run.

## 2026-08-17 — a marketplace listing build, six catches in one day

- **"7 PLACES" corrected a false claim into a different false claim.** A
  cover chip said "7 FOLDERS" (the tree showed 5 folders + 3 files); the
  fix wrote "7 PLACES," still wrong — the product has eight. Survived three
  review passes across two sessions, including one that explicitly
  reported the adjacent headline "verified correct" beside a panel of
  eight rows. Caught by the owner counting. Face 5 (number as label), face
  6 (self-reported verification). Produced the count drill.
- **A parallel design session's covers existed solely in its transcript.**
  Renders, review board, thumbnail strips — described in detail, never on
  disk. Caught by listing the workspace's files by mtime. Face 1.
  Confirmed the landing drill.
- **A sweep printed "none in text" from a grep that never ran.** An
  `unzip && grep` chain short-circuited on a warning exit code; the
  fallback line looked like a result. Caught because the output was
  suspiciously short — a rule the owner had written a month earlier after
  doing the same thing. Face 2. Confirmed the watched-check drill.
- **A required phrase nearly reported absent from the shipped archive.**
  A naive substring check returned False for BOTH the correct phrase and
  its wrong predecessor — the phrase wrapped across a source line. Caught
  because the double-False was impossible. Face 4 (normalization variant).
  Produced the whitespace-normalized form inside the negative drill.
- **A cover "scored 91/100, verified at 300px" — but the grid crops
  square.** At a center-square crop the headline lost its opening word. The
  verification had been run at the full canvas, a size no scrolling buyer
  ever sees. Caught by an outside session's critique, then confirmed by an
  actual crop test. Face 3. Produced the crop-condition rule: the
  thumbnail test runs on the cropped tile.
- **PDFs "verified clean" by string sweep — pixels said otherwise.** The
  text sweep passed while rendered pages showed literal `**` around bold
  phrases, doubled list markers, and a footer orphaned onto its own page.
  Caught by rendering every page to pixels and looking, specifically
  because a July string check had false-negatived on a letterspaced
  required notice (`R E S A L E`). Face 4, face 3.

## 2026-08-12 — the original "one law" day

- **Gallery PNGs committed without their generator.** The script lived in
  a discarded container; the next session transcribed code back out of the
  images. Face 1. Produced the convention that an artifact and its
  generator commit together.
- **A `check && append` chain silently did nothing** on a wrong path and
  the work was reported written. Face 2. Produced the read-back rule.
- **A quote shipped clipped AND unsourced** — the 300px strip made the
  truncation invisible, and two of six slides got full-size reads. Face 3.
  Produced "the strip tests legibility, not completeness."
- **A rule reported "not written anywhere" that existed** — the search had
  covered one guessed directory. Face 4. Produced the negative drill:
  catalog path, then whole-tree search.

## Earlier

- **July: the letterspaced false negative.** A substring check reported a
  required footer missing; it was present, letterspaced. The founding
  normalization scar — cited on 2026-08-17 when the same failure mode
  nearly recurred twice in one day.

## Not a face, but a cousin — a failed write destroyed state (2026-08-30)

- **A read-then-rewrite append blanked a day's log.** The write died
  mid-encode on a non-ASCII character, but the file had already been
  opened in truncate mode, so it was left empty and the retry re-added its
  own section alone. Not a false "done" — a tool that fails can still have
  destroyed state. Caught by the watched-check drill: the post-write byte
  count was suspiciously small for a multi-section file. Rules: append
  with an explicit UTF-8 encoding; never round-trip a file through a
  single failable write; a suspiciously small file after a write is a
  data-loss signal. Now a convention plus a checker FAIL (protected files
  that collapse below 40% of their `.bak`), which `icm-maintain` runs.
