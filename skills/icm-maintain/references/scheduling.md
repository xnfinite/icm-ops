---
type: reference
updated: 2026-09-08
---

# Scheduling the checker — three copy-paste lines

The checker is one file and needs Python 3.8 or newer, nothing else. Each
line below runs it from the workspace root, either writing the `--json`
object to `04-memory/last-check.json` (a session reads that file on
arrival) or printing the summary line. Replace the workspace path and the
skill folder with yours; the skill folder is usually
`.claude/skills/icm-maintain/`, `.agents/skills/icm-maintain/`, or
`~/.claude/skills/icm-maintain/`. `python3` on macOS and Linux; `python`
or `py` on Windows. Exit code `1` means at least one FAIL, so a scheduler
that alerts on non-zero exit alerts on drift.

## cron (macOS, Linux) — Mondays at 07:00

```
0 7 * * 1  cd /path/to/workspace && python3 .claude/skills/icm-maintain/scripts/icm_check.py . --json > 04-memory/last-check.json
```

## Windows Task Scheduler — Mondays at 07:00

```
schtasks /create /tn "icm-check" /sc weekly /d MON /st 07:00 /tr "cmd /c cd /d C:\path\to\workspace && python .claude\skills\icm-maintain\scripts\icm_check.py . --json > 04-memory\last-check.json"
```

## Session-start hook — print the summary line

```
python3 .claude/skills/icm-maintain/scripts/icm_check.py . | tail -n 1
```

Wire that command into whatever your harness runs when a session opens —
a hooks setting, a shell profile, a task runner — so the summary line
(`N FAIL / N WARN / N INFO`) is on screen before any work starts. On
Windows PowerShell, replace `| tail -n 1` with `| Select-Object -Last 1`.

## Notes

- A scheduled run only reads and reports. The maintenance run in
  `SKILL.md` — fixing what the authorized list allows, logging to
  `04-memory/maintenance-log.md`, refreshing `.bak` copies — is a session,
  not a cron line.
- "Scheduled" means created, persisted, AND observed to fire once
  (`icm-verifier`, face 6). Check the output file's timestamp after the
  planned time before reporting the schedule as working.
- `04-memory/last-check.json` is a machine artifact; give it a catalog row
  or add its folder's row to cover it, and keep it out of version control
  if the workspace is a repo.
