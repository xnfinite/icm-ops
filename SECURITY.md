# Security policy

This file says how to report a problem in icm-ops and what happens next. It
is a reporting policy and nothing more. This pack makes no security claims.

## Reporting a problem

Use GitHub's private vulnerability reporting on this repository (the
Security tab), if it is enabled. If that is unavailable, open an issue at
https://github.com/xnfinite/icm-ops/issues that names the file and omits the
details, and the maintainer replies with a channel to send them through.

Include what a bug report includes: operating system, `python --version`,
the exact command, and the checker's header line (the clock line).

## What to expect

- As of 2026-09-08 the maintainer aims to acknowledge a report within 14
  days. If no acknowledgement arrives, treat the repository as unmaintained:
  `CONTRIBUTING.md`, section Maintainer and continuity — the license lets
  you fork and fix.
- A fix, when one is made, ships as a patch or minor version and is noted
  in `CHANGELOG.md`, with credit to the reporter if they want it.
- There is no bounty.

## Supported versions

The newest 0.x release. Older releases are not patched; update by copying
the `skills/` folders again.

## Scope, as a fact

What this pack is, stated so a reporter can judge whether a problem belongs
here:

- The checker, `skills/icm-maintain/scripts/icm_check.py`, reads files under
  the root you name (plus `icm-ops.json` there, or the file given by
  `--config`), writes no files, and opens no network connection. Its output
  goes to stdout and stderr.
- The skills are markdown that an agent reads. They run nothing themselves;
  what an agent does after reading them is the agent's action in the
  agent's environment.
- There are no runtime dependencies, no install hooks and no telemetry.

A problem in any of the above is in scope. A problem in the harness that
loads the skills, in the model, or in a workspace's own content is not one
this repository can fix, though a pointer to where it belongs is welcome.
