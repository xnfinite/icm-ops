# Front Desk — working on icm-ops

You are in the repository of **icm-ops**, a pack of three Agent Skills that keep
an ICM workspace honest. This file is for a session working *on the pack*.
The skills themselves are for sessions working *inside a workspace*; read
them at `skills/<name>/SKILL.md`.

## What is here

| Path | What it is |
|---|---|
| `skills/icm-ledger/` | Score the agent's own advice: log with a falsifier before recommending, attach outcomes, run readouts, regenerate the "Know thyself" block. |
| `skills/icm-verifier/` | Check that claimed work is real before reporting it: the one law, the eight faces of a false "done", the drills, the report grammar. |
| `skills/icm-maintain/` | Keep the files true: `scripts/icm_check.py` (budgets, catalog coverage, links, clocks, staleness), compaction, the scheduled maintenance run. |
| `example/` | A minimal ICM workspace the checker passes. Copy it to start. |
| `example-broken/` | The same with five seeded defects the checker must name. |
| `scripts/test.py` | Frontmatter validity per the Agent Skills spec, both examples, the banned-phrase sweep. |

## Before you change anything

1. Run `python scripts/test.py` and watch it end with zero FAIL.
2. Read the skill you are changing in full; each one is under 250 lines on purpose.
3. Any number in `README.md` traces to a dated readout or to a command in this repo. Do not invent one.

## Rules

- ICM is Van Clief & McDermott's method (arXiv:2603.16021). The workspace
  builder is their `icm-architect`. This pack operates on what they build;
  credit them, link them, never present the method as ours.
- No "only / first / best," no security claims, no promise that an agent
  becomes correct. It becomes checkable and scorable.
- Commit freely with the agent's name in the trailer. Pushing, publishing,
  listing, and posting are the maintainer's actions.
- Every shipped file passes the sweep in `scripts/test.py`.
