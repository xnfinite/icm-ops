# Changelog

All notable changes to icm-ops are recorded here. The form is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html); the formats the
pack reads and writes are specified in `FORMAT.md`, and a change to anything
in its "Scope and stability" section is announced here one minor version
ahead of shipping.

## [Unreleased]

## [0.2.0] - 2026-09-08

Behaviour and formats change, so this is a minor version, not a patch. The
version string moves together in `.claude-plugin/plugin.json`, every
`skills/*/SKILL.md` `metadata.version`, `__version__` in
`skills/icm-maintain/scripts/icm_check.py` and this heading;
`scripts/test.py` asserts the four agree.

### Added

- `--today YYYY-MM-DD` pins the checker's clock, for tests and for
  reproducing an old report; the header line then says
  `clock overridden by --today`. `--version` prints `icm_check 0.2.0`.
- Exit code 3 for an internal error: the traceback goes to stderr, and with
  `--json` stdout still holds an object carrying an `error` key.
- `--json` keys `version` and `today`; readers ignore unknown keys.
- New WARN classes: a malformed date at any date site; a readout heading
  without a parseable date; a ledger id not zero-padded to three digits; a
  ledger entry lacking any of its six field lines (`CLAIM`, `CONFIDENCE`,
  `FALSIFIER`, `COST`, `REVIEW-BY`, `OUTCOME`) or a disagreement entry
  lacking `STAKES`, `KNOW-BY` or `RESOLVED`; a `hot_budgets` key that names
  no markdown file the walk found; a `.md` file in the ledger folder that
  is not a `YYYY-MM.md` month file (`BRIEFING.md`, `README.md` and
  `_TEMPLATE.md` excepted); an unterminated frontmatter block; a file that
  is not valid UTF-8, an unreadable file, an unlisted directory, or a
  skipped link or loop; a `BRIEFING.md` without a `readout:` field.
- Config errors (exit 2) for a path value that is absolute or carries a
  `..` segment, an empty `hot_budgets` key, and an `icm-ops.json` that
  exists but is not a file.
- INFO line `readouts found: N (newest YYYY-MM-DD)`, so a staleness check
  that switched itself off is visible; an INFO line for an absolute link
  left unchecked.
- Outcome word `MOOT`: the question dissolved before the falsifier could
  fire; counted apart from confirmed and disproven.
- `readout:` field in `BRIEFING.md` frontmatter; briefing staleness
  compares it to the newest readout.
- `FORMAT.md` (format 1): the ledger, disagreement, readout, briefing,
  checked-stamp and catalog-row grammars, the `icm-ops.json` keys, the
  checker's output contract, and the deprecation rule.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`; a bug-report
  issue template; a CI workflow that runs `scripts/test.py` on Ubuntu,
  Windows and macOS under Python 3.8, 3.10, 3.12 and current 3.x with no
  install step.
- `.gitattributes` and `.editorconfig`: LF line endings and UTF-8 without a
  byte-order mark, which the suite also checks.
- `skills/icm-maintain/assets/maintenance-log-template.md` and a "First
  run" paragraph in icm-maintain;
  `skills/icm-maintain/references/scheduling.md` (a cron line, a
  `schtasks` command, a session-start hook).
- `skills/icm-verifier/references/design-notes.md`: why the drills are
  shaped as they are and how a new face is designed before it costs
  anything.
- "First run" in icm-ledger; "Your first week" and "Support, stability,
  continuity" in the README.
- Test suite: usage errors exit 2, the exit-3 path, one version string
  everywhere, line endings and byte-order marks, a tripwire that compares
  `assets/icm-check.svg` with live checker output, config errors that exit
  2, and robustness cases on scratch copies of `example/`.

### Changed

- Ledger and disagreement keys, and the word `open`, are matched
  case-insensitively.
- Ledger ids are `L-` or `D-` plus three or more digits; the checker reports
  an id in full.
- The readout heading is recognised as `## Readout` followed by any
  non-digit separator and a date.
- A newest daily log dated ahead of the clock gets one day of grace before
  it FAILs.
- Link parsing follows CommonMark: titles, angle-bracket targets,
  percent-encoded paths and fragments; reference-style definitions
  (`[label]: path`) are checked; links inside fenced code, inline code
  spans and indented code are not scanned; absolute links are INFO, not
  FAIL.
- The frontmatter opener is a line that is exactly `---` (a `----` rule
  opens nothing), and the whole of an unterminated block is searched for
  `updated:`. The `.md` extension is matched case-insensitively in the
  walk.
- The checker reads each file once, tolerates a byte-order mark on
  `icm-ops.json`, and strips a `\\?\` prefix from the root argument.
- README: the install section opens with the copy-a-folder route; the demo
  block and the hero image are rendered from live output with the clock
  pinned; the numbers were re-derived on 2026-09-08 and are labelled as one
  operator's record.
- icm-maintain: the maintenance-log rule keeps as many run lines as fit
  under the budget; step 5 logs and step 6 backs up; the cadence is daily
  or weekly; a dead catalog row moves to the maintenance log under Needs
  owner.
- Unattended runs never attach outcomes or resolve disagreements, stated in
  both icm-maintain and icm-ledger.
- icm-verifier: the scar-log template runs newest first with one heading
  per date and a re-derived catch count; the scar log lives at a workspace
  path with a catalog row, not inside an installed skill folder.
- Both example fixtures carry `readout:` in `BRIEFING.md`; the example
  conventions state the catalog row grammar; the example READMEs show
  `--today`.

### Fixed

- `assets/icm-check.svg` carried a doubled percent sign in its background
  attribute.
- The checker crashed on a malformed date, an unreadable file, a directory
  named like a file, or a junction loop; each is now a WARN.
- A catalog over its hot budget was two FAILs for one defect; a catalog row
  with a `//` or `/./` segment, or one pointing inside a skipped link or
  loop, was reported as missing; a `deliverable_markers` entry written with
  backslashes never matched; a checked stamp wrapped across a blank line
  still matched in a CRLF file; the clock INFO line printed a negative age
  for a log dated ahead of the clock.
- icm-maintain's `deliverable_markers` default and its missing `log_dir`
  row disagreed with the code.
- The paper's title and the ledger counts in the README.

## [0.1.0] - 2026-09-08

Initial release. Three skills for an ICM workspace that already exists.

### Added

- **icm-ledger** — log consequential recommendations with a falsifier before
  giving them, attach outcomes, run readouts, regenerate the front-desk
  "Know thyself" block.
- **icm-verifier** — the one law and the eight faces of a false "done", the
  drills that defeat each, the report grammar, audit mode, and a scar-log
  template.
- **icm-maintain** — `icm_check.py` (frontmatter, catalog coverage, links,
  binding hot-file budgets, decision and ledger clocks, stale anchors,
  briefing staleness), the compaction routine, and the scheduled maintenance
  run with its authorized/never lists.
- `example/` (a minimal workspace the checker passes), `example-broken/`
  (five seeded defects it names), and `scripts/test.py`.

[0.2.0]: https://github.com/xnfinite/icm-ops/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/xnfinite/icm-ops/releases/tag/v0.1.0
