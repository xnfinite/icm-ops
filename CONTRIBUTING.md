# Contributing to icm-ops

icm-ops is three skills, one checker, two example trees and a test suite,
all plain files. Changes are welcome inside that scope. This file says how
to run the tests, what is out of scope, the house rules the suite enforces,
how formats change, how versions move, how to add a scar, and what happens
if the maintainer goes quiet.

## Run the tests

```
python scripts/test.py
```

Any Python 3.8 or newer; no install step and no dependencies, because the
suite is the proof that the checker runs on a bare interpreter. It validates
every `skills/*/SKILL.md` frontmatter, runs the checker on `example/`
(expects 0 FAIL) and on `example-broken/` (expects the seeded defects by
name, with the clock pinned by `--today`), parses `--json`, checks that the
version strings agree and that every file is LF without a byte-order mark,
and sweeps shipped files for banned phrases. CI runs the same command on
Ubuntu, Windows and macOS under four interpreters (3.8, 3.10, 3.12 and the
current 3.x). A pull request is ready when the suite ends `0 FAIL / 0 SKIP`
on your machine.

## Scope

The pack is: three skills (`icm-ledger`, `icm-verifier`, `icm-maintain`),
one checker (`skills/icm-maintain/scripts/icm_check.py`), two example trees
(`example/`, `example-broken/`) and the suite. In scope: fixes, clearer
wording, checks that fit the existing report, fixtures, and reports from
harnesses the maintainer has not run.

Out of scope, and not accepted as pull requests:

- a web dashboard;
- an MCP server;
- a builder or scaffold skill — the workspace is built with Van Clief and
  McDermott's `icm-architect`; this pack is a layer on top of the method;
- telemetry or install statistics;
- a checker in another language;
- a PyPI package, or any packaging that needs a build backend or a registry
  — the checker is one file; copy it;
- runtime dependencies of any kind.

Each item on that list puts something between the maintainer and the person
who copied a folder, and that something can break or disappear. The install
route that has to survive is `cp -r skills/* <wherever your agent reads
skills>`; nothing may stand in front of it.

## House rules

The suite enforces these. Read them before opening a pull request.

- **SKILL.md size and frontmatter.** Each `skills/*/SKILL.md` is at most 250
  lines and carries frontmatter per the Agent Skills spec: `name` equal to
  the folder name, `description` saying what the skill does and when to use
  it in at most 1024 characters, `license`, and `metadata` with `author` and
  `version`. Longer material goes in `references/` or `assets/` beside it.
- **The banned-phrase sweep.** `scripts/test.py` fails on superlative and
  exclusivity claims — no only/first/best, no accuracy claim that a dated
  readout did not produce — and on a short list of platform and personal
  names that belong in nobody's shipped file. State the limit in the same
  breath as the strength.
- **Line endings and encoding.** LF line endings and UTF-8 without a
  byte-order mark, in every file. `.gitattributes` sets `eol=lf` on every
  text file, `.editorconfig` tells editors the same, and the suite checks
  the bytes. If a clone shows CRLF (`git ls-files --eol` prints `w/crlf`),
  stage the normalized content and then let git rewrite the working tree
  from the index:

  ```
  git add --renormalize .
  git ls-files -z | xargs -0 rm -f
  git checkout -- .
  ```

  Run it from Git Bash on Windows. A bare `git checkout -- .` after that
  `git add` does not rewrite a file whose content already matches once
  normalized; deleting the tracked files forces the rewrite and keeps staged
  edits (verified with git 2.55 on 2026-09-08).
- **Credit.** Wherever a file explains ICM, it credits Van Clief and
  McDermott, arXiv:2603.16021 (https://arxiv.org/abs/2603.16021). The
  method is theirs; this pack composes with it.
- **Numbers.** A number on a shipping surface is re-derived by a command
  before it is written, and the command stays beside it where a reader
  could want it.

## Formats

`FORMAT.md` governs every artifact this pack reads or writes: ledger and
disagreement entries, readouts, `BRIEFING.md`, checked stamps, catalog rows,
`icm-ops.json` and the checker's output. Its "Scope and stability" section
lists what a user may build on. A change to anything in that section starts
as an issue, not a pull request. When accepted, it is announced as a
deprecation notice in `CHANGELOG.md` and the checker WARNs on the old form
from that version on; the change ships one minor version after its
deprecation notice, and the old form is removed only by a major version.
Additions that leave existing files valid — a key, a WARN class, an outcome
word — may arrive as a pull request with their CHANGELOG line and their
test.

## Versioning and releases

Versions follow SemVer. Four strings carry the version and move together, in
one commit:

- `version` in `.claude-plugin/plugin.json`;
- `metadata.version` in every `skills/*/SKILL.md`;
- `__version__` in `skills/icm-maintain/scripts/icm_check.py`;
- the newest `## [X.Y.Z] - YYYY-MM-DD` heading in `CHANGELOG.md`.

`scripts/test.py` asserts the four agree. Patch versions fix; minor versions
add (options, keys, WARN classes, fixtures, documents); a major version alone
removes or renames a stable surface. Git tags `vX.Y.Z` mark releases; the
maintainer pushes and tags. The date on a CHANGELOG heading is the day the
version was cut, not the day the work was done.

## Adding a scar

The verifier's drills exist because a false "done" got past a review once.
If one gets past you and the pack should learn from it, add one dated entry
in the format of `skills/icm-verifier/references/scar-log-template.md`:
newest first, one heading per date, one bullet per catch naming what was
claimed, what was true, how it was caught, the face (1 to 8) and the rule it
produced or confirmed. Name the ledger id (`L-NNN`) when the same event is
also a judgment failure. Anonymize platforms, products and figures; keep the
date and the shape of the failure, because the shape is the lesson. A catch
that fits no face is worth an issue before a pull request — a new face is
designed before it costs anything.

## Maintainer and continuity

The copyright holder is Nightflow Systems and the GitHub account is
xnfinite; those are one party, not two. Issues and pull requests go to
https://github.com/xnfinite/icm-ops; a problem you would rather not post in
public follows `SECURITY.md`; conduct follows `CODE_OF_CONDUCT.md`.

If the maintainer is unreachable: the license is MIT, so fork it and keep
going. Everything needed is in this folder — the skills are markdown, the
checker is one file of standard-library Python, the formats are written down
in `FORMAT.md`, and the tests run with one command. There is no service,
registry or account that can go away and take the pack with it; the
copy-a-folder install route needs neither the maintainer nor any registry.
