# session-leases

When several agent sessions work on one machine, some resources take one
session at a time: the desktop, an editor that accepts one client, a branch
being pushed, the scheduled tasks. Two sessions reaching for one of them at
once is an accident of timing that neither can see coming. This mod puts a
lease in front of the action, so coordination does not depend on an agent
remembering a rule.

Before a tool call that touches a shared resource, the mod claims it for the
session through `lease.py` (shipped beside this file, and in
`skills/icm-maintain/scripts/`):

- **Free, or already this session's:** the call runs. A *hold* lease (the
  desktop, an editor) keeps renewing while the session uses the resource and
  ends when the session leaves it idle for the rule's minutes. A *call* lease
  (a push, a scheduled-task change) is released when the call returns.
- **Held by another session:** the call is refused. The refusal names the
  holder and its reason, so the agent can message that session or do
  something else first.

It also checks ledger ids at the moment of the write. An Edit or Write that adds
a `## L-NNN` or `## D-NNN` heading to a `<ledger dir>/YYYY-MM.md` file is refused
when that id is already in any month file, with the next free id named. Two
sessions that read the same newest id would otherwise both take the next one.

A session's identity is its session id, so the session's own claims renew
instead of colliding. A lease taken by hand with a name
(`python lease.py take editor --who "<name>" --why "<what>"`) keeps that name
when the mod renews it, so other sessions know whom to ask.

## Rules

Three resources are on by default: a `git push` (`git-<repo folder>`),
scheduled-task changes (`scheduled-tasks`: the PowerShell ScheduledTask
cmdlets, `schtasks /create|change|delete`, `crontab` edits) and computer-use
tools (`desktop`). A machine adds its own in `<lease dir>/config.json`:

```json
{
  "python": "python",
  "rules": [
    { "resource": "editor", "command": "(?:^|[\\s;&|(\\\\/])build-editor\\b", "mode": "hold", "minutes": 45 }
  ]
}
```

A rule matches a tool by `tool` (a regular expression on the tool name,
default the Bash and PowerShell tools when `command` is given) and, for a
shell, by `command` (a case-insensitive regular expression on the command
line). A config rule that reuses a default's resource name replaces that
default. `lease_tool` points at another copy of `lease.py`; `python` skips the
interpreter probe.

The lease folder is `ICM_LEASE_DIR`, else `%LOCALAPPDATA%/icm-leases` on
Windows, else `$XDG_STATE_HOME/icm-leases` (default
`~/.local/state/icm-leases`). It is per machine and outside any synced
folder: a resource on one machine means nothing on another.

## Limits

- It fails open. If no Python is found or the lease tool cannot run, the call
  goes ahead with one note to the agent per session. A coordinator that broke
  must not stop work that a working one would allow.
- It sees tool calls. Work started outside a session (a scheduled job, a
  person at the keyboard) takes its lease with `lease.py` itself, or not at
  all.
- A command pattern is text, so a shell line that only mentions a program
  can still match. The patterns ask for the program name at the start of a
  word or after a path separator, which keeps a grep or a commit message from
  claiming anything.
- Claude Code only, by the plugin route: `/plugin install session-leases@icm-ops`.

Tests: `claude plugin test plugins/session-leases`.
