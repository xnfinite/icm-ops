# icm-gates

A change to a guarded file does not go live until its own tests pass on that exact content.

When agents write the code, the work moves from writing it to checking it, and the check that
gets skipped is the one at the worst moment: the suite not run before the install. This plugin
makes the install command itself the checkpoint.

- **Before an install, deploy or publish command** named in the workspace's `icm-gates.json`, it
  runs that gate's suite on the files as they stand. A pass lets the command run and is
  remembered for that exact content; a failure refuses it with the suite's last lines; a file
  over the gate's size limit is refused until it is split.
- **After a write to a gated file**, it notes a file that went over its limit, and once per
  session asks for a second reader who did not write the change.
- **The `icm-gates` skill** says how to set gates up, write the short rules file a reviewer
  checks against, run the second reader, and check one result outside the loop that made it.

It is opt-in twice: installed on its own, and inactive in any workspace without an
`icm-gates.json`. It does not read or change the icm-ops core, its checker or `icm-ops.json`.

```
/plugin install icm-gates@icm-ops
```

## Configure

`icm-gates.json` at the workspace root, or the file `ICM_GATES_CONFIG` names:

```json
{ "gates": [ { "name": "publish-service", "files": ["admin/publish.py"],
               "test": ["python", "admin/tests/run.py"], "install": "\\binstall-publish\\.sh\\b",
               "max_lines": 400, "rules": "admin/PUBLISH-RULES.md" } ] }
```

## Check it

```
claude plugin validate plugins/icm-gates
claude plugin test plugins/icm-gates
```

The tests run the hooks against a mocked workspace: no config gates nothing; a pass installs and
is remembered for that content; changed content reruns the suite; a failure, a missing file, a
broken gate, a suite that cannot run and a file over its limit each refuse; ordinary commands
are never gated; a gated write asks once for a second reader.

MIT.
