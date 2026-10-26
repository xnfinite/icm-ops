# More than one session on a machine

Several agent sessions can work on one machine at once: two in the same
workspace, one building while another reviews, a scheduled maintenance run in
the middle of a person's working session. Files are the easy part. The hard
part is the machine. A desktop, an editor that takes one client, a branch
being pushed and the scheduled tasks are each one thing that two sessions can
reach for at the same moment, and neither can see the other coming.

The design property that removes the accident: **every shared resource has an
owner of the moment, and a session that needs it can find the owner and ask.**
Three pieces give that.

## Presence: who else is working

The agent's own session listing shows which sessions are live, which are busy,
and the name each answers to. Read it on arrival and before anything shared.

## Leases: who holds a resource right now

`scripts/lease.py` (standard library, Python 3.8+) holds a lease per resource
in a machine-local folder outside any synced tree. Taking one is an exclusive
file create, so two takers can never both hold it; the test suite starts eight
at once and requires exactly one winner.

    python lease.py take editor --who "<your session's name>" --why "build 80" --minutes 90
    python lease.py release editor
    python lease.py list

- Take the lease before you act, with a name another session can message.
- Long work renews by taking again. A renewal never shortens a lease and keeps
  the name already on it.
- **Held: ask, do not collide.** The tool prints the holder and its reason.
  Message that session, and do something else meanwhile. Never break a live
  lease; an expired one is broken by the next taker and kept in `stale/`.
- Release when done. A session that dies holding one is covered by the expiry,
  so keep `--minutes` honest.

Name resources once, lowercase with dashes, and keep the list where the
workspace's sessions read it: `desktop`, `editor`, `gpu`, `git-<repo>`,
`scheduled-tasks`, `disk-moves`, and `<other-workspace>` for files another
workspace's sessions own.

The `session-leases` mod (Claude Code) puts the lease in front of the action:
before a git push, a scheduled-task change, a computer-use action or a command
named in the machine's `config.json`, it claims the lease for the session and
refuses the call while another session holds it. The mod fails open; the
paragraph above still holds wherever it is not installed.

## Shared files: append, never rewrite

The daily log, the ledger, STATE and the catalog are written by every session.

- Edit, never regenerate. Read the on-disk copy right before the edit.
- Add your own dated section rather than rewriting another session's.
- Take a ledger id at the moment of writing, in the same edit. The checker
  WARNs on an id used twice, because outcomes and readouts cite entries by id.

## Another workspace's things

Files, folders and scheduled jobs another workspace owns belong to its
sessions. If one is live, message it and let it make the change. If none is,
take the lease, make the change, and leave a dated note in that workspace's
log the same turn, so its next session finds it.

## What goes wrong without it

The shapes, from one operator's record (October 2026):

- two sessions driving one editor at once: the machine stopped with a memory
  error;
- two sessions pushing one branch at once: both pushes rejected, an hour lost;
- one session changing another workspace's scheduled tasks mid-build: it held
  only because the other session read the log before re-registering them.

Each time, the session that arrived later had no way to know another was
already there.
