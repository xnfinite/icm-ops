---
type: reference
updated: 2026-09-08
---

# Conventions

Read before your first write in a session. These rules keep the workspace
cheap to read; the checker (`99-meta/README.md`) enforces the ones it can.

## Frontmatter

Every markdown file opens with YAML frontmatter, except the front desk
(`CLAUDE.md`, `AGENTS.md`) and a root `README.md`:

```yaml
---
type: context | process | decision | source | memory | artifact | reference | catalog
updated: YYYY-MM-DD
---
```

Decisions add `status:` and `review-by: YYYY-MM-DD`. A decision with no
review date is a rule nobody will re-examine.

## Naming

- Lowercase, hyphenated: `weekly-close.md`, not `Weekly Close.md`.
- Verb-first for processes. Numbered prefixes only where order matters
  (decisions, top-level folders).
- Daily logs are `04-memory/log/YYYY-MM-DD.md`; ledger months are
  `04-memory/ledger/YYYY-MM.md`.

## File size

Target under 200 lines; past 400 a file is doing two jobs, split it. Hot files
carry binding budgets in `icm-ops.json` (STATE 250, CATALOG 155,
maintenance-log 60): over budget fails the check and the fix is compaction,
not a bigger budget.

## Catalog rows

A row is `` | `path/from/root` | read when | ``. Several paths in one cell are
joined by ` / `, each in backticks; folders end in `/`. Paths are relative
to the root, without `./`, `..` or an absolute prefix, and spelled
case-exact on every operating system: the checker treats every backticked
token in that cell as a path and looks it up in the tree it walked. Grammar:
FORMAT.md in the icm-ops repo, "Catalog rows".

## Linking

Relative paths, always. `[the ledger](../04-memory/ledger/2026-09.md)` from a
file in `02-processes/`. The checker fails on any relative link that does not
resolve.

## External numbers

A figure that came from outside this workspace carries a stamp on the same
line or the next: `checked: YYYY-MM-DD · source · stale after: N days`. The
checker warns when the window has blown.
