# icm-ops formats (format 1)

ICM — Interpretable Context Methodology — is Van Clief and McDermott's method
(arXiv:2603.16021, https://arxiv.org/abs/2603.16021): a folder of plain
markdown with a front desk, a catalog and dated files, which an agent walks
instead of loading whole. icm-ops is a layer on top of that method, not part
of it, and this file specifies the artifacts icm-ops adds on top: the advice
ledger and its readouts, the computed briefing, the checked stamp on an
external number, the catalog row grammar the checker parses, the
`icm-ops.json` configuration, and what the checker prints and returns. It is
written so that a reader with no other document and no maintainer to ask can
produce files the checker accepts and parse what it emits. Where another file
in this repository disagrees with this one, this one is right and the other
has a bug worth an issue.

## Scope and stability

This is **format 1**, in force from icm-ops 0.2.0. The format number moves
only when a major version removes or renames something listed here.

Stable surfaces — build on these and expect them to hold across minor and
patch versions:

- the catalog row grammar (Catalog rows);
- the ledger field names `CLAIM`, `CONFIDENCE`, `FALSIFIER`, `COST`,
  `REVIEW-BY`, `OUTCOME`; the disagreement field names `STAKES`, `KNOW-BY`,
  `RESOLVED`; and the outcome words (sections Ledger entries and
  Disagreement entries);
- the readout heading (Readouts);
- the `BRIEFING.md` frontmatter fields (BRIEFING.md);
- the checked stamp (Checked stamps);
- the `icm-ops.json` keys and their defaults (icm-ops.json);
- the exit codes 0, 1, 2 and 3 (Checker output);
- the `--json` keys (Checker output);
- the line prefixes `[FAIL] `, `[WARN] `, `[INFO] ` and the summary line
  `N FAIL / N WARN / N INFO` (Checker output).

May change without notice, in any version: the wording of a finding after
its prefix, the set and text of INFO lines, and the header line. A script
that reads the human report keys on the prefix and the summary line; a
script that wants more uses `--json`. Do not parse the sentence that follows
a prefix.

## Dates and the clock

A date is exactly `YYYY-MM-DD`: four digits, a dash, two digits, a dash, two
digits, and a real calendar date — `2026-02-30` is malformed. One
surrounding pair of matching quotes (`"2026-09-08"` or `'2026-09-08'`) is
tolerated wherever a date is read. Anything else is malformed: `20260908`,
`2026-9-8`, `08/09/2026`, `2026-W37-2`, a placeholder `YYYY-MM-DD` left in.
A malformed date produces a WARN naming the file and the value (the
frontmatter and daily-log sites keep their own wording, below), after which
the checker skips the comparison that needed the date and carries on. A
malformed date never ends a run.

The checker's clock is the machine's local calendar date, or the value of
`--today YYYY-MM-DD` when that option is given; the header line then
contains `clock overridden by --today`. Every comparison below uses that
clock and nothing else.

| Site | Fires when |
|---|---|
| `REVIEW-BY:` or `KNOW-BY:` on an entry still open | the date is strictly before the clock (WARN) |
| `review-by:` in a decision's frontmatter | the date is on or before the clock (WARN) |
| a checked stamp | (clock − checked) exceeds N days (WARN) |
| `readout:` in `BRIEFING.md` | older than the newest readout (FAIL) |
| the newest daily log, `YYYY-MM-DD.md` in `log_dir` | dated more than one day after the clock (FAIL); the one day of grace covers time zones. A file in `log_dir` whose name is date-shaped but not a real date is a WARN; a name that is not date-shaped is not read as a log at all. |

`--today` exists so a test can pin its verdicts and so an old report can be
reproduced on a later day. A malformed `--today` value is a usage error
(exit 2).

## Frontmatter

Frontmatter is the block between an opening line that is exactly `---`
(after an optional UTF-8 byte-order mark; leading blank lines and blank
space are tolerated) and the next line that is exactly `---`; trailing
whitespace on either fence is tolerated. A line that merely starts with
`---` — a `----` rule, `---title` — opens nothing. The checker reads the
whole block, never a byte prefix, so a long field early in the block cannot
hide a later one. Inside the block each field is `key: value` on its own
line; keys are matched case-insensitively.

- `updated:` — required, with a date, in every markdown file the checker
  walks, except root files named in `frontmatter_exempt` (default
  `CLAUDE.md`, `AGENTS.md`, `README.md`) and files whose path contains a
  `deliverable_markers` substring. Absent: a WARN naming the file.
  Malformed: a WARN naming the file and the value, worded around
  `updated:`.
- `review-by:` — required in addition, with a date, in decision records
  (files in `decisions_dir` whose name starts with a digit). Absent:
  `[WARN] decision without review-by date`; malformed: the malformed-date
  WARN; on or before the clock: `[WARN] decision DUE FOR REVIEW`.
- `type:` — conventional (`catalog`, `context`, `decision`, `process`,
  `memory`, `reference`, `artifact`); the checker does not read it.
- A file named `_TEMPLATE.md` may carry the placeholder `YYYY-MM-DD` and is
  not checked for a date.
- No block at all: `[WARN] missing frontmatter: <file>`. A block that opens
  and never closes: `[WARN] unterminated frontmatter: <file>`; the checker
  still looks for `updated:` in the text that follows the opening line.

## Catalog rows

The catalog (`catalog` key; default `00-catalog/CATALOG.md`) is a markdown
table whose leading cell names a path and whose next cell says when to read
it:

```
| `path/from/root` | read when |
```

- The leading cell holds one or more backticked paths. Several are joined
  by ` / ` — space, slash, space: `` `CLAUDE.md` / `AGENTS.md` ``.
- Every backticked token in that cell is a path. Prose belongs in the other
  cell; a backticked word in the leading cell that is not a path is
  reported as a missing path.
- Folders end with `/` (`04-memory/log/`). A folder row covers every file
  under it.
- Paths are relative to the workspace root, with forward slashes, without a
  leading `./`, without a `..` segment, and without an absolute prefix. The
  checker collapses a stray `./`, `//` or `/./`; a `..` segment or an
  absolute prefix is a WARN, and that row covers nothing.
- Spelling is case-exact on every operating system, and the catalog's
  spelling is canonical: if the file on disk differs from its row by case,
  rename the file. A case-insensitive filesystem may let the mismatch pass
  today; the same workspace on a case-sensitive one breaks.

Rows drive two checks. A row whose path does not exist is
`[FAIL] catalog row points at missing path: <path>`. Every markdown file the
checker walks needs coverage — its own row or an ancestor folder's row — and
a file without it is `[WARN] no catalog coverage ... <file>`; exempt from
coverage are `README.md` files, `_TEMPLATE.md`, files inside the catalog's
own folder, root files in `frontmatter_exempt`, and deliverable-marked
files. The catalog is also held to its own line rule: with a hot budget B on
it, WARN past B − 5 lines and FAIL past B + 15; without one, WARN past 150
and FAIL past 170. Over its hot budget, the binding-budget FAIL is the one
finding; the own-rule line is not added on top of it.

## Ledger entries

Ledger files are `<ledger_dir>/YYYY-MM.md` (default `04-memory/ledger/`),
one per month, append-only, entries in the order they were written. Any
other `.md` file in that folder — apart from `BRIEFING.md`, `README.md` and
`_TEMPLATE.md` — is a WARN and is not read as a ledger, so a month file
named `2026-9.md` cannot hide its entries in silence. An entry (indented
here for display; in the file every line starts at the margin):

    ## L-NNN · YYYY-MM-DD · <source>
    CLAIM: the recommendation, stated so it can lose.
    CONFIDENCE: low | medium | high
    FALSIFIER: the observable event that would prove it wrong.
    COST: cheap | hours | days | money | platform | relationship
    REVIEW-BY: YYYY-MM-DD
    OUTCOME: open

- **Heading.** `## L-NNN · YYYY-MM-DD · <source>` — the id, the date the
  entry was written, and the adviser (`builder`, `advisor`, or a named
  agent), separated by ` · ` (U+00B7). An entry reconstructed after the
  fact from a dated log carries an optional trailing
  ` · retro: <path of the dated log>`; that is the one permitted exception
  to logging before advising.
- **Id.** `L-` plus at least three digits, zero-padded to three — `L-007`,
  `L-042`, `L-1003` — continuous across month files and never reused. The
  checker reads the whole number; an id with fewer than three digits is a
  WARN.
- **Extent.** An entry is the text from its `## ` heading to the next line
  that starts with `## `, of any kind; the id immediately follows `## `.
  Where a block holds a key twice, the `REVIEW-BY` (or `KNOW-BY`) line
  nearest the heading is the one read.
- **Field lines**, each starting a line, conventionally in this order:
  `CLAIM`, `CONFIDENCE`, `FALSIFIER`, `COST`, `REVIEW-BY`, `OUTCOME`. All
  six are required: a missing field line is a WARN naming the entry and the
  field. The order is a convention the checker does not check. A value may
  continue on following lines. Keys are uppercase by convention and matched
  case-insensitively.
- **CONFIDENCE.** The leading word is the enum — `low`, `medium` or `high`;
  anything after it is free text (`high (asserted in a ship report)`).
  Words, never percentages.
- **COST.** The leading word is the enum — `cheap`, `hours`, `days`,
  `money`, `platform` or `relationship`; anything after it is free text
  (`money (a month of the starter tier) and relationship`). What each class
  means and the verification it owes:
  `skills/icm-ledger/assets/readout-template.md`.
- **REVIEW-BY.** The date follows the colon immediately. Every entry expires
  into review; an open entry whose date is strictly before the clock is
  `[WARN] ledger L-NNN past its date ... and still open`.
- **OUTCOME.** `OUTCOME: open` while open (`open` matched
  case-insensitively). Otherwise `OUTCOME: <WORD> [YYYY-MM-DD] [— evidence]`
  — the word, optionally the date the outcome was attached, optionally an
  em dash and the evidence. WORD is one of:

  | Word | Meaning |
  |---|---|
  | `CONFIRMED` | the falsifier had its chance and did not fire |
  | `CONFIRMED-IN-SCOPE` | held on what was tested; the broader claim is untested |
  | `DISPROVEN` | the falsifier fired; cite the evidence |
  | `MIXED` | part held, part fired; say which was which |
  | `AVERTED` | caught wrong before it was issued or acted on |
  | `EXPIRED` | the review date passed with no outcome attached |
  | `MOOT` | the question dissolved before the falsifier could fire; counted apart from confirmed and disproven |

- **Amendment.** An extra line inside the entry,
  `AMENDED YYYY-MM-DD: <what changed and why>`, with the original lines left
  untouched. Entries are never rewritten or deleted; wrong calls are the
  record.

What the checker reads: the id, the `REVIEW-BY` date, whether `OUTCOME`'s
leading word is `open`, and whether each of the six field lines exists. It
does not judge the text of CLAIM, FALSIFIER or COST, does not check the
order of the lines, and does not check that the outcome word is one of the
seven; a readout does that.

## Disagreement entries

When the owner overrides an adviser, or two advisers oppose each other on a
consequential call, the disagreement is logged in the same month file
(indented here for display; in the file every line starts at the margin):

    ## D-NNN · YYYY-MM-DD · A (source): position vs B (source): position
    STAKES: what rides on it, in both directions.
    KNOW-BY: YYYY-MM-DD — the event that settles it.
    RESOLVED: open

- **Heading.** `## D-NNN · YYYY-MM-DD · A (source): position vs B (source):
  position` — each party named with its source in parentheses and its
  position, the two joined by ` vs `.
- **Id.** Same rule as ledger entries, with `D-`: at least three digits,
  zero-padded to three, continuous across months, never reused. `L-` and
  `D-` are separate sequences.
- **Field lines**, each starting a line, conventionally in this order:
  `STAKES`, `KNOW-BY`, `RESOLVED`; all three required (a missing one is the
  same WARN as for a ledger entry); order not checked; keys matched
  case-insensitively.
- **KNOW-BY.** The date immediately after the colon, then the settling
  event. An open entry whose date is strictly before the clock gets the
  past-its-date WARN.
- **RESOLVED.** `RESOLVED: open` while open. Otherwise
  `RESOLVED: A | B | both-partly — evidence`: the leading word names who was
  right — `A`, `B` or `both-partly` — then an em dash and the evidence.
  Resolutions score both sides. Resolving takes both parties present; an
  unattended pass never resolves a D-entry.

## Readouts

A readout is the periodic count of the record, written at the bottom of the
month file it counts, under this heading (indented here for display; in the
file it starts at the margin):

    ## Readout — YYYY-MM-DD (n=N, counts only)

The date is the day the readout was computed, read from the clock; `n` is
the number of entries counted. What follows is prose with counts and entry
ids, never percentages under n=20 (structure:
`skills/icm-ledger/assets/readout-template.md`).

The checker recognises `## Readout` (case-insensitive) followed by any
non-digit separator of at most 20 characters — an em dash, a hyphen, a
middle dot, a colon — and a date. The newest such date across every month
file is "the newest readout", which the briefing check compares against. A
`## Readout` heading with no parseable date is
`[WARN] readout heading without a parseable date`, because the alternative
is a staleness check that switches itself off in silence. Whenever the
ledger directory exists the checker prints
`[INFO] readouts found: N (newest YYYY-MM-DD)`, or `readouts found: 0` —
an INFO line, so its wording is not a stable surface (Scope and stability);
it is there for a person reading the report.

## BRIEFING.md

`<ledger_dir>/BRIEFING.md` is the self-briefing computed from the newest
readout and regenerated in the same action as the readout (template:
`skills/icm-ledger/assets/briefing-template.md`). Its frontmatter:

```
---
type: memory
updated: YYYY-MM-DD
readout: YYYY-MM-DD
---
```

- `updated:` — the date the file was last edited.
- `readout:` — the date of the readout the briefing was computed from.

Staleness: the checker compares `readout:` with the newest readout and
FAILs when `readout:` is older — a stale correction wearing a fresh voice.
When `readout:` is absent it compares `updated:` instead and adds a WARN
saying that format 1 wants `readout:`. A value that does not parse — a
placeholder left in, a malformed date — while a readout exists is a FAIL.
When no month file holds a readout, the briefing is not checked for
staleness. The front-desk "Know thyself" block in `CLAUDE.md` and
`AGENTS.md` is regenerated from the same readout; the checker does not read
it.

## Checked stamps

A number that came from outside the workspace — a platform's figure, a
vendor's window, a price — carries, in the working file that states it:

```
checked: YYYY-MM-DD · source · stale after: N days
```

- `checked:` and the date the value was read at its source; then the
  source; then `stale after:` and a whole number of days. The stretch from
  the date to `stale after:` is at most 120 characters, on one line or
  wrapped once (a line break, never a blank line).
- The checker reads stamps in working files only; historical records
  (`historical_dirs`, ledger month files, deliverables) are skipped. When
  (clock − checked) exceeds N days:
  `[WARN] STALE ANCHOR in <file>: checked <date>, window <N>d blown by <M>d`.
  A malformed date is the malformed-date WARN.

A blown window means the number describes the past while reading as the
present: re-check at the source or remove the number.

## icm-ops.json

An optional JSON object at the workspace root (or the file named by
`--config PATH`). Every key is optional; a key left out takes its default.
Paths are relative to the workspace root with forward slashes. A UTF-8
byte-order mark at the start of the file is tolerated.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `hot_budgets` | map, path → integer > 0 | `04-memory/STATE.md`: 250, `00-catalog/CATALOG.md`: 155, `04-memory/maintenance-log.md`: 60 | Binding line budgets (`wc -l` semantics). Over budget is a FAIL; at or under is an INFO line with the count. A key that names no markdown file the walk found is a WARN: a budget guarding nothing is a rule switched off, usually by a typo. |
| `protected` | list of paths | `CLAUDE.md`, `AGENTS.md`, `00-catalog/CATALOG.md`, `00-catalog/CONVENTIONS.md`, `04-memory/STATE.md`, `04-memory/ledger/BRIEFING.md`, `04-memory/maintenance-log.md` | Files the maintenance run copies to `<file>.bak` after a clean check, and the checker guards: a protected file below 40 % of a `.bak` larger than 400 bytes is a FAIL. The newest ledger month and the newest daily log are guarded as well. |
| `deliverable_markers` | list of path substrings | empty | A path containing one is deliverable content: exempt from the coverage and frontmatter rules, and on size treated as a historical record — never a FAIL, a WARN past twice `size_target_lines`. A marker is a substring, not a path: it may start with `/`, and backslashes in it are read as forward slashes. Example: `["/product/", "/sample/"]`. |
| `frontmatter_exempt` | list of file names | `CLAUDE.md`, `AGENTS.md`, `README.md` | Root-level files that need no frontmatter and no catalog row. |
| `size_target_lines` | integer > 0 | 200 | Working files WARN past it and FAIL past twice it; historical records WARN only. |
| `historical_dirs` | list of folders | `04-memory/log/` | Records, not working files: oversize is a WARN there and checked stamps are not read. Ledger month files are historical as well. |
| `log_dir` | path | `04-memory/log` | Daily `YYYY-MM-DD.md` logs; the clock check reads the newest name. |
| `ledger_dir` | path | `04-memory/ledger` | Month files, readouts and `BRIEFING.md`. |
| `decisions_dir` | path | `01-context/decisions` | Numbered decision records carrying `review-by:`. |
| `catalog` | path | `00-catalog/CATALOG.md` | The map. It must exist, or the checker exits 2 — a folder with no catalog is not an ICM workspace. |

Validation is strict and every violation is a config error, exit 2:
`hot_budgets` values must be positive integers and its keys non-empty, list
keys must hold non-empty strings, `size_target_lines` must be a positive
integer, path keys must be non-empty strings, and a file that is not a JSON
object — or an `icm-ops.json` that exists but is not a file — is rejected.
Every path value (`hot_budgets` keys, `protected`, `historical_dirs`,
`log_dir`, `ledger_dir`, `decisions_dir`, `catalog`) must stay inside the
workspace: an absolute prefix or a `..` segment is a config error. An
unknown key is a config error too, and the message lists the known keys.
That is deliberate: a misspelled key that silently did nothing would be a
rule switched off by a typo. It also means a config written for a newer
checker fails loudly on an older one, which is the failure to prefer.

The walk: every `*.md` file under the root (the extension matched
case-insensitively; the catalog's spelling of a name stays case-exact),
skipping folders whose name starts with `.` and the folders `node_modules`
and `__pycache__`; links, junctions and directory loops are skipped with a
WARN, and a catalog row pointing inside one is checked against the
filesystem instead. A file that cannot be read is a WARN and drops out of
later checks; a file that is not valid UTF-8 is reported once, its bad
bytes replaced, and stays in every check. Neither ends the run. Relative
links are checked in inline links and in reference definitions
(`[label]: path`), with code stripped first — fenced blocks, inline code
spans, and lines indented four spaces or a tab after a blank line.
`example/icm-ops.json` is a complete config with every default written
out.

## Checker output

```
python <skill folder>/scripts/icm_check.py [workspace-root] [--json] [--config PATH] [--today YYYY-MM-DD]
python <skill folder>/scripts/icm_check.py --version
```

The skill folder is wherever the skill was installed —
`.claude/skills/icm-maintain/`, `.agents/skills/icm-maintain/`,
`~/.claude/skills/icm-maintain/`, or `skills/icm-maintain/` in a clone of
this repository. The workspace root defaults to the current directory.

**Exit codes.** `0` — no FAIL finding. `1` — at least one FAIL. `2` — usage
or config error: a message and the usage line on stderr, nothing on stdout.
`3` — internal error: the traceback on stderr; with `--json`, stdout still
holds an object with `version`, `today`, `fail`, `warn`, `info` and `error`,
so a reader that parses stdout never meets a half-written report.

**Human report** (stdout, the default): a header line, a blank line, one
line per finding, a blank line, the summary line. Finding lines start with
`[FAIL] `, `[WARN] ` or `[INFO] ` and are grouped in that order. The summary
line is `N FAIL / N WARN / N INFO`. In 0.2.0 the header reads
`icm_check <version> run <date> on <root folder> (config: icm-ops.json) —
dates are claims; this line is the clock` (`(defaults)` when there is no
config file), with ` (clock overridden by --today)` after the date when the
option was given. The header is not a stable surface; the prefixes and the
summary line are.

**`--json`** (stdout, and nothing else on stdout): one object with keys in
this order — `version` (the checker's version string), `today` (the clock,
`YYYY-MM-DD`), `fail`, `warn`, `info` (lists of strings, each the finding
text without its prefix). Readers ignore unknown keys; no key is removed or
renamed inside a major version; new keys may arrive in a minor version.

**Options.** `--json`; `--config PATH` (also `--config=PATH`; the file must
exist); `--today YYYY-MM-DD` (also `--today=YYYY-MM-DD`; pins the clock — a
malformed value is exit 2); `--version` prints `icm_check X.Y.Z` and exits
0; `-h` or `--help` prints the usage. Any other option is exit 2.

The checker is read-only: it writes no files and opens no network
connection. It needs Python 3.8 or newer and the standard library, nothing
else.

## Compatibility and deprecation

icm-ops follows SemVer. Four strings carry the version and move together:
`version` in `.claude-plugin/plugin.json`, `metadata.version` in every
`skills/*/SKILL.md`, `__version__` in
`skills/icm-maintain/scripts/icm_check.py`, and the newest heading in
`CHANGELOG.md`; `scripts/test.py` asserts they agree.

- **Additions** — a key, an option, a WARN class, an outcome word, a
  `--json` key — arrive in minor versions and are listed in `CHANGELOG.md`.
  Existing files stay valid; existing readers keep working because they
  ignore what they do not know.
- **Removing or renaming** anything listed under Scope and stability is
  announced one minor version ahead in `CHANGELOG.md`; from that version the
  checker WARNs on the deprecated form while still accepting it. Only a
  major version removes the old form, and the format number moves with it.
- **Patch versions** fix crashes and wording and add nothing listed under
  Scope and stability.

Proposing a change to a stable surface: `CONTRIBUTING.md`, section Formats.
It starts as an issue, not a pull request.
