---
name: icm-gates
description: Put a gate in front of code that goes live, so a change to it ships only after its own tests pass on that exact content, it stays under a size limit, and a second reader who did not write it has looked. Use when (1) a workspace has code or config whose install, deploy or publish affects other people or other agents (a service, a guard, a release script); (2) the icm-gates mod refused an install or noted a gated write; (3) setting up icm-gates.json for a workspace; (4) a change to gated code is about to be called done; or (5) the owner asks how AI-written changes get checked before they ship.
license: MIT
metadata:
  version: "0.1.0"
---

# icm-gates

When agents write the code, the work moves from writing it to checking it. The checks that get
skipped are the ones at the worst moment: the suite that was not run before the install, the
file that grew one more responsibility, the change only its author read. This skill and its mod
put those checks at the install itself. It is part of icm-ops and opt-in: a workspace without an
`icm-gates.json` is untouched, and nothing here changes the ledger, the verifier, the checker
or `icm-ops.json`.

## Set up a gate

Write `icm-gates.json` at the workspace root (or point `ICM_GATES_CONFIG` at one):

```json
{
  "gates": [
    {
      "name": "publish-service",
      "files": ["admin/publish.py", "admin/publish_npm.py"],
      "test": ["python", "admin/tests/run_publish_tests.py"],
      "install": "\\binstall-publish\\.sh\\b",
      "max_lines": 400,
      "rules": "admin/PUBLISH-RULES.md",
      "timeout_minutes": 10
    }
  ]
}
```

- `files`: every file the install ships. Relative paths are from the workspace root.
- `test`: the suite, as an argv list, run from the workspace root. It must exit 0 only when
  everything the gate protects still holds. One suite per gate, runnable with one command.
- `install`: a regular expression that matches the shell command that makes the change live.
- `max_lines`: the size past which a file must be split before it installs. Start near 400; a
  file that does four jobs is four files.
- `rules`: a short file of the invariants the code must keep (below). Optional, and worth it.

## What the mod does

- **At the install command.** It reads the gate's files. Over `max_lines`: refused, split first.
  If this exact content already passed its suite, the install runs. Otherwise the mod runs the
  suite itself; exit 0 lets the install run and remembers the content, anything else refuses it
  with the suite's last lines. A suite that cannot run refuses too: a gate fails closed.
- **At a write to a gated file.** A note if the file is now over its limit, and once per gate per
  session a reminder that the change needs a second reader.

It is a checkpoint for an honest agent under momentum, not a wall against a hostile one.

## The rules file

Ten lines or fewer of what must stay true however the code changes. For example: "Root never
runs code a lower-privilege user can write." "A token is never a process argument." "Every
refusal happens before anything leaves the machine." "A result is checked where it lands,
never on the exit code alone." The second reader checks the change against this file, and a
new rule is added each time a review or an incident finds one that was missing.

## The second reader

Before a gated change is called done, someone who did not write it reads it. With an agent:

1. Start a fresh reader (a subagent, or another session) with **only** the diff, the rules
   file, and the suite's output. Not the author's explanation, plan or commit message: a reader
   who is told what the change does finds what it was told.
2. Ask it to find what would break a rule, a caller, or a case the tests do not cover, and to
   say "none found" only after naming what it checked.
3. Fix what it finds, add a test for each finding, and run the suite again.

Record the review in the session's log with what it checked. A review that found nothing and
names nothing it checked did not happen.

## Anchor one number outside the loop

Tests written by the same agent that wrote the code prove the code agrees with its author. For
anything that ships, check at least one result where it lands, outside the loop that made it:
the registry that should now serve the version, the API that should now show the change, the
file the other program reads. A self-consistent system proves its pipes; an outside number
proves the work. (This is `icm-verifier`'s law applied to code: a claim is not reportable until
observed where it will be consumed.)

## Keep the gates honest

- A failing suite is fixed in the code, never by weakening the test or the gate.
- Delete one-off probes once their finding is a test; scattered scripts are where review stops.
- Raise `max_lines` only with a written reason; splitting is almost always the answer.
- When the mod refuses, read the reason before anything else. Routing around a gate is the
  failure it exists to prevent.
