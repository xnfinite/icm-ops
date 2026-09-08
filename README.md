# icm-ops — skills that keep an ICM workspace honest

**For Claude Code, Codex, Cursor, and any agent that reads the Agent Skills format: a ledger that scores the agent's advice, a verifier that checks its work before it reports "done", and a maintenance run that keeps the files true.**

You built the workspace with [icm-architect](https://github.com/RinDig/icm-architect), or by hand from the [ICM paper](https://arxiv.org/abs/2603.16021). This is the layer that runs it afterwards, when the sessions that follow start trusting files that have quietly gone stale, reporting work that never landed on disk, and giving confident advice that nobody ever scores.

Works with: **Claude Code · Codex · Cursor · Gemini CLI · GitHub Copilot · OpenCode · Goose · Amp · Roo Code · JetBrains Junie · OpenHands · Letta** — everything on the [Agent Skills client list](https://agentskills.io). Three folders of markdown and one Python script. No runtime dependencies, no telemetry, MIT.

## Install

```bash
npx skills add xnfinite/icm-ops
```

That installs all three skills into `.claude/skills/` (Claude Code) or `.agents/skills/` (Codex, Cursor, OpenCode, Zed…); add `-g` for global. Other paths:

```bash
# Claude Code plugin
/plugin marketplace add xnfinite/icm-ops
/plugin install icm-ops@icm-ops

# or copy a single skill
cp -r skills/icm-verifier ~/.claude/skills/
```

Then run the checker on your workspace once, so you know where you stand:

```bash
python skills/icm-maintain/scripts/icm_check.py path/to/your/workspace
```

## What it looks like when it is working

This is the block the ledger writes into the front desk of one real workspace, regenerated from its own readouts. Every session that opens the workspace reads it first:

> **Know thyself.** You have a track record here, and it is not clean. As of the 2026-08-25 readout (n=19):
>
> - **Working sessions** reliably fail one way: numerals and absolutes on shipping surfaces, asserted without the one-step-away check (5 of 5 failures). Count or probe FIRST, then write the sentence.
> - **Reviewing sessions** fail two ways: verdicts about state past their instruments (three times — read what your tool says it does NOT cover before reporting absence), and closure carried past its evidence — the costliest error in the book was nine verified-true searches and a wrong "channel is dead." Before declaring anything dead or absent: name the frame your search inherited, run one search that abandons it.

Nobody wrote that by hand. It is what three weeks of logged calls, attached outcomes, and a readout produce.

## The three skills

| Skill | The rule it enforces | What it gives the next session |
|---|---|---|
| **icm-ledger** | No consequential recommendation without a falsifier, logged *before* the advice is given. Outcomes attach when reality shows up. | A monthly ledger, cost-weighted readouts, and the "Know thyself" block above. |
| **icm-verifier** | A claim is not reportable until verified by observation at the point where it will be consumed. | The eight faces of a false "done", one drill per face, a report grammar, and audit mode for other sessions' reports. |
| **icm-maintain** | Files carry binding budgets; over budget fails the build; compaction moves, never deletes. | `icm_check.py`, the compaction routine, and a scheduled maintenance run with explicit "authorized to fix" and "never" lists. |

### icm-ledger — score the advice, not just the work

Every entry is written so it can lose:

```
## L-036 · 2026-09-02 · builder
CLAIM: The public headline (56% token saving) is the schema-deferred upper
bound and overstates what the library delivers on a standard host …
CONFIDENCE: high — the arithmetic reproduces from existing exports.
FALSIFIER: the spec lets a host omit inputSchema as a normal mode; or an
independent re-derivation disagrees by more than rounding.
COST: relationship — a public number gets much smaller.
REVIEW-BY: 2026-09-09
OUTCOME: CONFIRMED-IN-SCOPE 2026-09-03 — tested against the spec; …
```

Outcomes are one of `CONFIRMED`, `CONFIRMED-IN-SCOPE`, `DISPROVEN`, `MIXED`, `AVERTED`, `EXPIRED`. A readout counts them by adviser and by cost class and writes the sentence that matters ("reliable most of the time, and wrong about the expensive ones"). Disagreements between advisers, or between an adviser and the owner, are logged as D-entries. Wrong calls are never deleted; they are the asset.

### icm-verifier — the eight faces of a false "done"

Container work that never hit disk. The short-circuited check that printed a clean result from a step that never ran. Verified in the wrong place: right artifact, wrong size, crop, or copy. The false negative after one guessed directory, or a search blind to a letterspaced wordmark. The numeral read as a label, and the agreeable number nobody counted. Self-reported verification with no observation named. Premature closure: true premises, wrong conclusion, nine honest searches and a wrong "channel is dead." The closed loop: a check that shares its source with the claim it checks. Each face has a drill; each drill exists because that face got past a review once. The report grammar is two sentences: "Done, verified by [observation]" or "Done, unverified." Never a bare done.

### icm-maintain — the workspace fixes its own errors

![icm_check.py naming the five seeded defects in example-broken](assets/icm-check.svg)

```
$ python skills/icm-maintain/scripts/icm_check.py example-broken
[FAIL] broken relative link in 04-memory/STATE.md: (../02-processes/does-not-exist.md)
[FAIL] 04-memory/STATE.md: 258 lines — OVER its binding budget of 250. Run the compaction routine.
[FAIL] BRIEFING.md (2026-08-01) is OLDER than the newest ledger readout (2026-09-08) — regenerate it and the front-desk block
[WARN] no catalog coverage (own row or ancestor folder row): 02-processes/orphan.md
[WARN] ledger L-003 past its date (2026-08-01) and still open — resolve or mark EXPIRED (2026-09.md)
... 13 INFO lines omitted ...
3 FAIL / 2 WARN / 13 INFO
```

Budgets bind (over = FAIL, and the checker never raises one). Compaction is the one subtractive operation and it is staged for a human, never applied unattended. A daily maintenance session runs the checker, fixes only what the "authorized" list allows, backs up the protected files only after a clean run, and logs one line, because the immune system must not become the disease. Configure paths and budgets in an optional `icm-ops.json` at the workspace root; the defaults are the ICM conventions.

## With and without

| An ICM workspace… | without icm-ops | with icm-ops |
|---|---|---|
| Advice the agent gave last week | gone with the session | logged with a falsifier, scored when reality arrives |
| "Done" from a parallel session | taken on faith | audited claim by claim at the consumption point |
| STATE.md after a month | 270 lines nobody reads | 250 by rule, compacted by a routine with receipts |
| A stale number in a hot file | trusted | stamped `checked: date · source · stale after: N days`, flagged when blown |
| What the next session knows about its own failure modes | nothing | the "Know thyself" block, regenerated from readouts |

## Numbers — one operator's record, not a benchmark

Three weeks (2026-08-17 → 2026-09-08), one workspace, two advisers (a working session and a reviewing session), 42 ledger entries and 3 disagreement entries. Of the 17 resolved so far: 7 disproven, 4 confirmed, 2 confirmed in scope only, 3 mixed, 1 averted. That readout (n=19) found the working session's five disproven calls were all one failure class, which is how the block above got written. That is the whole point: the number that matters was not the accuracy rate, it was the *shape* of the errors, and no one could see it until they were logged.

These are one person's calls in one workspace. They say nothing about your agent until you log yours.

## Try it on the example

```bash
git clone https://github.com/xnfinite/icm-ops
cd icm-ops
python scripts/test.py                                       # spec-valid skills, both examples, the banned-phrase sweep
python skills/icm-maintain/scripts/icm_check.py example      # 0 FAIL
python skills/icm-maintain/scripts/icm_check.py example-broken   # names the five seeded defects
```

`example/` is a complete minimal workspace: front desk, catalog, conventions, state, one decision, a six-entry ledger with a readout, a briefing, a maintenance log. Copy it to start, or point the checker at the workspace you already have.

## What it does not do

- It does not build a workspace. That is [icm-architect](https://github.com/RinDig/icm-architect), by the method's author.
- It does not make an agent correct. It makes claims checkable and advice scorable; the agent can still be wrong, and now you find out.
- It is not a safety or security product and makes no such claims.
- The ledger only works if someone attaches outcomes. A ledger nobody scores is a diary.

## Credits

ICM — Interpretable Context Methodology: Folder Structure as Agent Architecture — is [Jake Van Clief and David McDermott's](https://arxiv.org/abs/2603.16021); the [official repo](https://github.com/RinDig/Interpretable-Context-Methodology) and [icm-architect](https://github.com/RinDig/icm-architect) are theirs. icm-ops is the operating layer one practitioner built on top of it and ran daily for three weeks before packaging it.

If it saves you one bad call, star the repo. If you want it installed and tuned in your own workspace, the maintainer does that as a service; see the repository's About links.

MIT © Nightflow Systems
