#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Nightflow Systems
"""Leases: one session at a time on a shared resource of this machine.

When several agent sessions work on one machine, a lease says who is using a
shared resource right now, why, and until when: the desktop, an editor that
takes one client at a time, a git push, the scheduled tasks. Taking one is
atomic (the lease file is created exclusively), so two sessions can never both
hold it. The protocol around it: references/sessions.md in this skill.

    python lease.py take git-myrepo --who "docs session" --why "push the release"
    python lease.py take editor --why "build 80" --minutes 90
    python lease.py release editor
    python lease.py check git-myrepo
    python lease.py list

A session is known by --session, which defaults to the CLAUDE_CODE_SESSION_ID
environment variable, and by --who, a name another session can message (the
name the agent's session listing shows). Taking again with the same session
or the same name renews; a renewal never shortens a lease and keeps the name
already on it. An expired lease is broken by the next taker and kept in
stale/. Every take, renew, release and break goes to history.log.

Leases live on this machine only, outside any synced folder: ICM_LEASE_DIR if
set, else %LOCALAPPDATA%/icm-leases on Windows, else
$XDG_STATE_HOME/icm-leases (default ~/.local/state/icm-leases).

Exit codes: 0 done or free, 1 held by another session, 2 usage error.
Standard library only, Python 3.8 and newer. The same file ships in
skills/icm-maintain/scripts/ and plugins/session-leases/; keep them identical.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

__version__ = "1"  # the lease file format: who, why, since, expires, session

RESOURCE = re.compile(r"[a-z0-9][a-z0-9-]{0,47}")
MAX_MINUTES = 12 * 60


def lease_dir():
    if os.environ.get("ICM_LEASE_DIR"):
        return Path(os.environ["ICM_LEASE_DIR"])
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "icm-leases"
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "icm-leases"


def stamp(t):
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


def read(p):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and "expires" in d else None
    except (OSError, ValueError):
        return None


def describe(resource, d):
    left = (d["expires"] - time.time()) / 60
    state = ("until %s (%.0f min left)" % (stamp(d["expires"]), left) if left > 0
             else "EXPIRED at %s" % stamp(d["expires"]))
    who = d.get("who") or "an unnamed session"
    sid = d.get("session") or ""
    return '%s: %s%s, since %s, for "%s", %s' % (
        resource, who, " (session %s)" % sid[:8] if sid and sid[:8] not in who else "",
        stamp(d.get("since", 0)), d.get("why", ""), state)


def same_holder(cur, a):
    if a.session and cur.get("session"):
        return cur["session"] == a.session
    return bool(a.who_given) and cur.get("who") == a.who


def history(root, line):
    with open(str(root / "history.log"), "a", encoding="utf-8") as f:
        f.write("%s %s\n" % (stamp(time.time()), line))


def create_exclusive(p, data):
    fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # FileExistsError if held: the atomic part
    try:
        os.write(fd, json.dumps(data).encode("utf-8"))
    except OSError:
        os.close(fd)
        p.unlink(missing_ok=True)
        raise
    os.close(fd)


def break_expired(root, p, cur):
    stale = root / "stale"
    stale.mkdir(exist_ok=True)
    dest = stale / ("%s-%d.json" % (p.stem, time.time_ns()))
    try:
        os.replace(str(p), str(dest))
    except FileNotFoundError:
        return  # another session broke it first; the retry decides who takes it
    print("broke an expired lease: %s; kept in %s" % (describe(p.stem, cur), dest))
    history(root, "BREAK %s (expired; was %s: %s)" % (p.stem, cur.get("who"), cur.get("why")))


def take(root, a):
    p = root / (a.resource + ".json")
    for _ in range(5):
        now = time.time()
        data = {"who": a.who, "why": a.why, "since": now, "expires": now + a.minutes * 60,
                "session": a.session}
        try:
            create_exclusive(p, data)
            print("took %s until %s" % (a.resource, stamp(data["expires"])))
            history(root, "TAKE %s by %s: %s (%d min)" % (a.resource, a.who, a.why, a.minutes))
            return 0
        except FileExistsError:
            pass
        cur = read(p)
        if cur is None:  # mid-write by another session, or damaged: look again before judging
            time.sleep(0.2)
            cur = read(p)
            if cur is None:
                break_expired(root, p, {"who": "?", "why": "unreadable lease file", "expires": 0})
                continue
        if same_holder(cur, a):
            data["since"] = cur.get("since", now)
            data["expires"] = max(cur["expires"], data["expires"])
            if not a.who_given:
                data["who"] = cur.get("who") or a.who
            if a.why.startswith("auto:") and cur.get("why"):
                data["why"] = cur["why"]
            data["session"] = a.session or cur.get("session", "")
            tmp = p.with_name("%s.%d.tmp" % (p.name, os.getpid()))
            tmp.write_text(json.dumps(data), encoding="utf-8")
            os.replace(str(tmp), str(p))
            print("renewed %s until %s" % (a.resource, stamp(data["expires"])))
            history(root, "RENEW %s by %s: %s (%d min)" % (a.resource, data["who"], a.why, a.minutes))
            return 0
        if cur["expires"] > time.time():
            print("HELD: " + describe(a.resource, cur))
            print('Message the holder (by the name above, or the busy session working on that) '
                  'or do something else first. Never break a live lease.')
            return 1
        break_expired(root, p, cur)
    print("could not take %s: other sessions kept racing for it; try again" % a.resource, file=sys.stderr)
    return 1


def release(root, a):
    p = root / (a.resource + ".json")
    cur = read(p)
    if cur is None:
        print("%s is not held" % a.resource)
        return 0
    if not same_holder(cur, a):
        print("NOT YOURS: " + describe(a.resource, cur))
        return 1
    p.unlink(missing_ok=True)
    print("released %s" % a.resource)
    history(root, "RELEASE %s by %s" % (a.resource, cur.get("who")))
    return 0


def check(root, a):
    cur = read(root / (a.resource + ".json"))
    if cur and cur["expires"] > time.time():
        print("HELD: " + describe(a.resource, cur))
        return 1
    print("%s is free%s" % (a.resource, " (an expired lease is waiting to be broken)" if cur else ""))
    return 0


def list_all(root, a):
    held = [(p.stem, read(p)) for p in sorted(root.glob("*.json"))]
    held = [(r, d) for r, d in held if d]
    for r, d in held:
        print(describe(r, d))
    if not held:
        print("no leases held")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lease.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    for name in ("take", "release", "check"):
        s = sub.add_parser(name)
        s.add_argument("resource")
        if name != "check":
            s.add_argument("--who", help="a name another session can message")
            s.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
                           help="this session's id (default: $CLAUDE_CODE_SESSION_ID)")
        if name == "take":
            s.add_argument("--why", required=True, help="what you are about to do")
            s.add_argument("--minutes", type=int, default=60)
    sub.add_parser("list")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.error("say take, release, check or list")
    if getattr(a, "resource", None) is not None and not RESOURCE.fullmatch(a.resource):
        ap.error("resource names are lowercase words joined by dashes, e.g. editor or git-myrepo (got %r)"
                 % a.resource)
    if a.cmd == "take" and not 1 <= a.minutes <= MAX_MINUTES:
        ap.error("--minutes must be 1-%d; renew a long job instead of taking a day" % MAX_MINUTES)
    if a.cmd in ("take", "release"):
        a.who_given = bool(a.who)
        if not a.who:
            if not a.session:
                ap.error("give --who (or run inside a session that sets CLAUDE_CODE_SESSION_ID)")
            a.who = "session " + a.session[:8]
    root = lease_dir()
    root.mkdir(parents=True, exist_ok=True)
    return {"take": take, "release": release, "check": check, "list": list_all}[a.cmd](root, a)


if __name__ == "__main__":
    sys.exit(main())
