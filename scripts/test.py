#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Nightflow Systems
"""icm-ops test runner. Standard library only, Python 3.8 and newer. Run
from anywhere:

    python scripts/test.py

Prints one [PASS] / [FAIL] line per assertion and a summary
(`N PASS / N FAIL / N SKIP`; nothing skips — a missing file is a FAIL);
exits 1 on any FAIL. What it checks:

  (a) every expected skills/*/SKILL.md exists (a missing one is a FAIL), is
      at most 250 lines, and has spec-valid frontmatter: name equals the
      folder, matches ^[a-z0-9]+(-[a-z0-9]+)*$ and is at most 64 chars;
      description non-empty and at most 1024; license present.
  (b) icm_check.py on example/ with the clock pinned to 2026-09-08 exits 0
      with 0 FAIL / 0 WARN.
  (c) icm_check.py on example-broken/ with the clock pinned exits 1, names
      all five seeded defects (see example-broken/README-BROKEN.md), reports
      exactly 3 FAIL / 2 WARN and says the clock was overridden. One run on
      the real clock asserts only the exit code and the five defects, since
      the fixture's review dates pass with time.
  (d) --json on example/ (pinned) parses; its keys include fail, warn and
      info, each a list, and it carries version and today.
  (e) the clock-driven design, pinned: example/ with --today 2027-01-01
      still exits 0 and reports L-005 past its date.
  (f) usage errors exit 2 with nothing on stdout (a missing root, an unknown
      option, an invalid --today); --version prints the version; an internal
      error inside run() returns 3 and --json still yields an object with an
      error key.
  (g) one version string across .claude-plugin/plugin.json, every SKILL.md
      metadata.version, __version__ in icm_check.py and the newest
      CHANGELOG heading.
  (h) hygiene: no text file in the tree carries a CR byte or starts with a
      BOM; neither .py source holds a raw U+FEFF character.
  (i) assets/icm-check.svg is a render of the live checker output on
      example-broken/: its [FAIL] and [WARN] lines and its FAIL / WARN
      counts (the INFO count and the header are presentation), with no
      doubled percent sign.
  (j) a case-insensitive banned-phrase sweep over shipped files (the mods in
      hooks/, plugins/ and types/ included) finds zero hits.
  (k) robustness: scratch copies of example/ carrying malformed dates, odd
      ids, a loose readout heading, unterminated frontmatter, CommonMark link
      forms (inline, reference definitions, code that is not scanned), a BOM
      in icm-ops.json, directories named like files, review-by edge cases, a
      ledger entry missing field lines, a hot_budgets key naming no file, a
      catalog over its budget, a stray file in the ledger folder, an .MD
      extension, a `----` rule, doubled slashes in a catalog row, a log a
      day ahead and a CRLF stamp never crash the checker: empty stderr, a
      summary line and --json that parses, in every case. Stray names in the
      log folder never stand in for the newest log, a stamp is read whatever
      `checked:` precedes it, and a D-entry past KNOW-BY is never told to be
      marked EXPIRED.
  (l) config errors exit 2 with nothing on stdout: an absolute path or a
      `..` segment in a path key, an empty hot_budgets key, an icm-ops.json
      that is a directory.
  (m) lease.py, in a scratch lease folder: take, refuse another session,
      renew by the holder's session without losing its name or shortening
      it, release only by the holder, break and keep an expired lease, log
      every move, usage errors exit 2, and eight sessions taking at once
      leave exactly one winner; a second session arriving between a read
      and a break or release never ends with two holders or a lost lease;
      every documented command line runs as written outside a session; the
      name "config" is refused. With ICM_LEASE_DIR unset the folder is the
      profile's .icm-leases on Windows, never AppData. Its copy in
      plugins/session-leases/ is byte-identical.
"""
import contextlib
import html
import importlib.util
import io
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKER = ROOT / "skills" / "icm-maintain" / "scripts" / "icm_check.py"
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BANNED = re.compile(
    r"can.t hallucinate|cannot hallucinate|hallucination.free|unhackable|the only|"
    r"the first|the best|nobody else|upwork|etsy|fiverr|connects\b|"
    r"skool|reddit\.com", re.I)
SWEEP = ["README.md", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
         "CODE_OF_CONDUCT.md", "FORMAT.md", ".claude-plugin", "assets", "skills", "example",
         "example-broken", "hooks", "plugins", "types"]
SKIP_DIRS = {".git", ".icm", "node_modules", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".toml", ".svg"}
TEXT_NAMES = {".editorconfig", ".gitattributes", ".gitignore"}
SKILLS = ["icm-ledger", "icm-verifier", "icm-maintain"]
SKILL_MAX_LINES = 250
TODAY = "2026-09-08"  # the fixtures' clock; every exact verdict below is pinned to it
DEFECTS = [
    ("defect 1: STATE.md over its binding budget",
     re.compile(r"^\[FAIL\] 04-memory/STATE\.md: \d+ lines .*OVER its binding budget", re.M)),
    ("defect 2: orphan.md has no catalog coverage",
     re.compile(r"^\[WARN\] no catalog coverage.*02-processes/orphan\.md", re.M)),
    ("defect 3: broken link to does-not-exist.md",
     re.compile(r"^\[FAIL\] broken relative link in 04-memory/STATE\.md: \(.*does-not-exist\.md\)", re.M)),
    ("defect 4: L-003 past its date and still open",
     re.compile(r"^\[WARN\] ledger L-003 past its date", re.M)),
    ("defect 5: BRIEFING older than the newest readout",
     re.compile(r"^\[FAIL\] BRIEFING\.md .*OLDER than the newest ledger readout", re.M)),
]

counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def report(status, msg):
    counts[status] += 1
    print(f"[{status}] {msg}")


def check(cond, msg):
    report("PASS" if cond else "FAIL", msg)
    return bool(cond)


def read_text(p):
    return p.read_text(encoding="utf-8", errors="replace")


def count_lines(text):
    """wc -l semantics, the same definition icm_check.py enforces."""
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def parse_frontmatter(text):
    """Minimal YAML-ish frontmatter reader: top-level `key: value` pairs.
    Continuation lines (folded scalars, nested maps) are appended to the
    previous key so presence and length can be judged."""
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    fields, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if m and not line[0].isspace():
            key = m.group(1)
            fields[key] = m.group(2).strip()
        elif key is not None:
            fields[key] = (fields[key] + " " + line.strip()).strip()
    for k, v in fields.items():
        v = re.sub(r"^[>|][-+]?\s*", "", v)
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        fields[k] = v.strip()
    return fields


def run_checker(*args):
    p = subprocess.run([sys.executable, str(CHECKER), *args], cwd=str(ROOT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def summary(out):
    return re.search(r"^(\d+) FAIL / (\d+) WARN / (\d+) INFO$", out, re.M)


def checker_version():
    m = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"', read_text(CHECKER), re.M) if CHECKER.is_file() else None
    return m.group(1) if m else None


def stderr_note(err):
    return (" stderr: " + err.strip()) if err.strip() else ""


# --- (a) skills -------------------------------------------------------------

def test_skill_frontmatter():
    skills_dir = ROOT / "skills"
    folders = [skills_dir / name for name in SKILLS]
    if skills_dir.is_dir():
        folders += sorted(p for p in skills_dir.iterdir() if p.is_dir() and p.name not in SKILLS)
    for folder in folders:
        skill = folder / "SKILL.md"
        rel = f"skills/{folder.name}/SKILL.md"
        if not check(skill.is_file(), f"{rel}: present"):
            continue
        text = read_text(skill)
        n = count_lines(text)
        check(n <= SKILL_MAX_LINES, f"{rel}: {n} lines, at most {SKILL_MAX_LINES}")
        fm = parse_frontmatter(text)
        if not check(fm is not None, f"{rel}: frontmatter block present"):
            continue
        name = fm.get("name", "")
        check(name == folder.name, f"{rel}: name {name!r} equals folder name")
        check(bool(SKILL_NAME.match(name)) and len(name) <= 64,
              f"{rel}: name matches ^[a-z0-9]+(-[a-z0-9]+)*$ and is <= 64 chars")
        desc = fm.get("description", "")
        check(0 < len(desc) <= 1024, f"{rel}: description non-empty and <= 1024 chars ({len(desc)})")
        check(bool(fm.get("license")), f"{rel}: license present")


# --- (b) (c) (d) (e) the fixtures, clock pinned -----------------------------

def test_example_clean():
    if not check(CHECKER.is_file(), f"checker present at {CHECKER.relative_to(ROOT).as_posix()}"):
        return
    code, out, err = run_checker('example', '--today', TODAY)
    check(code == 0 and not err.strip(), f"example/ (pinned): exit code 0, empty stderr (got {code}){stderr_note(err)}")
    m = summary(out)
    check(m is not None and (m.group(1), m.group(2)) == ("0", "0"),
          f"example/ (pinned): summary line reports 0 FAIL / 0 WARN (got {m.group(0) if m else 'no summary line'})")


def test_example_broken():
    if not CHECKER.is_file():
        return
    code, out, err = run_checker('example-broken', '--today', TODAY)
    check(code == 1, f"example-broken/ (pinned): exit code 1 (got {code}){stderr_note(err)}")
    header = out.splitlines()[0] if out else ""
    check(f"run {TODAY} (clock overridden by --today)" in header,
          "example-broken/ (pinned): header line says the clock was overridden")
    for label, pattern in DEFECTS:
        check(pattern.search(out) is not None, f"example-broken/ (pinned): {label}")
    m = summary(out)
    check(m is not None and (m.group(1), m.group(2)) == ("3", "2"),
          f"example-broken/ (pinned): exactly 3 FAIL / 2 WARN (got {m.group(0) if m else 'no summary line'})")
    code, out, err = run_checker('example-broken')
    check(code == 1, f"example-broken/ (real clock): exit code 1 (got {code}){stderr_note(err)}")
    check(all(pattern.search(out) for _, pattern in DEFECTS),
          "example-broken/ (real clock): all five defects named, whatever the date")


def test_json():
    if not CHECKER.is_file():
        return
    code, out, err = run_checker('example', '--json', '--today', TODAY)
    try:
        data = json.loads(out)
    except ValueError as e:
        check(False, f"example/ --json: stdout parses as JSON ({e})")
        return
    keys = sorted(data) if isinstance(data, dict) else type(data).__name__
    check(isinstance(data, dict) and {"fail", "warn", "info"} <= set(data),
          f"example/ --json: keys include fail / warn / info (got {keys})")
    check(all(isinstance(data.get(k), list) for k in ("fail", "warn", "info")),
          "example/ --json: fail, warn and info are lists")
    check(data.get("fail") == [] and code == 0, "example/ --json: fail list empty and exit 0")
    ref = checker_version()
    check(data.get("version") == ref and data.get("today") == TODAY,
          f"example/ --json: version {data.get('version')!r} is icm_check.py's {ref!r} and today is {data.get('today')!r}")


def test_future_clock():
    if not CHECKER.is_file():
        return
    code, out, err = run_checker('example', '--today', '2027-01-01')
    check(code == 0 and "ledger L-005 past its date" in out,
          f"example/ --today 2027-01-01: exit 0 and L-005 reported past its date (got {code}){stderr_note(err)}")


# --- (f) exit codes 2 and 3, --version ---------------------------------------

def test_usage_errors():
    if not CHECKER.is_file():
        return
    cases = [
        ("a missing root", (str(ROOT / "no-such-workspace"),)),
        ("an unknown option", ('example', '--bogus')),
        ("an invalid --today", ('example', '--today', '2026-02-30')),
    ]
    for label, args in cases:
        code, out, err = run_checker(*args)
        check(code == 2 and out == "" and err.strip() != "",
              f"usage error exits 2 with nothing on stdout: {label} (got {code})")
    ref = checker_version()
    code, out, err = run_checker('--version')
    check(code == 0 and out.strip() == f"icm_check {ref}",
          f"--version prints icm_check {ref} and exits 0 (got {out.strip()!r}, {code})")


def test_internal_error():
    if not CHECKER.is_file():
        return
    sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
    spec = importlib.util.spec_from_file_location("icm_check_under_test", str(CHECKER))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001 - any import failure is the finding
        check(False, f"icm_check.py imports in-process ({type(e).__name__}: {e})")
        return

    def boom(root, cfg, today):
        raise RuntimeError("synthetic failure for the exit-3 test")

    mod.run = boom
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mod.main([str(ROOT / "example"), '--json', '--today', TODAY])
    check(rc == 3, f"internal error in run(): main() returns 3 (got {rc})")
    try:
        data = json.loads(out.getvalue())
    except ValueError:
        data = None
    check(isinstance(data, dict) and "error" in data and data.get("fail") == [] and "version" in data,
          "internal error with --json: stdout is an object with fail / warn / info, version and an error key")
    check("RuntimeError" in err.getvalue(), "internal error: the traceback goes to stderr")


# --- (g) one version everywhere ---------------------------------------------

def test_version_sync():
    ref = checker_version()
    if not check(ref is not None, 'icm_check.py: __version__ = "X.Y.Z" present'):
        return
    places = []
    pj = ROOT / ".claude-plugin" / "plugin.json"
    if pj.is_file():
        try:
            v = json.loads(read_text(pj)).get("version", "<missing>")
        except ValueError:
            v = "<unparseable>"
    else:
        v = None
    places.append((".claude-plugin/plugin.json version", v))
    for name in SKILLS:
        skill = ROOT / "skills" / name / "SKILL.md"
        v = None
        if skill.is_file():
            block = re.search(r"^metadata:[ \t]*\n((?:[ \t]+[^\n]*\n)+)", read_text(skill), re.M)
            vm = re.search(r"version:[ \t]*[\"']?([^\"'\s]+)", block.group(1)) if block else None
            v = vm.group(1) if vm else "<missing>"
        places.append((f"skills/{name}/SKILL.md metadata.version", v))
    cl = ROOT / "CHANGELOG.md"
    if cl.is_file():
        hm = re.search(r"^## \[(\d+\.\d+\.\d+)\]", read_text(cl), re.M)
        v = hm.group(1) if hm else None
        label = "CHANGELOG.md newest ## [X.Y.Z] heading"
    else:
        v, label = None, "CHANGELOG.md"
    places.append((label, v))
    for label, v in places:
        check(v == ref, f"version sync: {label} is {v!r}; icm_check.py __version__ is {ref!r}")


# --- (h) line endings and BOMs -----------------------------------------------

def test_line_endings():
    hits, scanned = [], 0
    for dirpath, dirnames, filenames in os.walk(str(ROOT)):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            p = pathlib.Path(dirpath) / fn
            if p.suffix.lower() not in TEXT_SUFFIXES and fn not in TEXT_NAMES:
                continue
            scanned += 1
            rel = p.relative_to(ROOT).as_posix()
            try:
                raw = p.read_bytes()
            except OSError as e:
                hits.append(f"{rel}: unreadable ({e})")
                continue
            if b"\r" in raw:
                hits.append(f"{rel}: CR byte")
            if raw.startswith(b"\xef\xbb\xbf"):
                hits.append(f"{rel}: BOM")
    for h in hits:
        print(f"       hygiene: {h}")
    check(not hits, f"line endings: no CR byte and no BOM across {scanned} text files ({len(hits)} found)")
    for p in (ROOT / "scripts" / "test.py", CHECKER):
        if p.is_file():
            check("\ufeff" not in read_text(p), f"{p.relative_to(ROOT).as_posix()}: no raw U+FEFF character in the source")


# --- (i) the hero image is live output ---------------------------------------

def test_svg_tripwire():
    svg = ROOT / "assets" / "icm-check.svg"
    if not check(svg.is_file(), "svg tripwire: assets/icm-check.svg present"):
        return
    if not CHECKER.is_file():
        return
    text = read_text(svg)
    spans = [html.unescape(s).strip() for s in re.findall(r"<tspan[^>]*>(.*?)</tspan>", text, re.S)]
    if not check(any("--today" in s for s in spans),
                 "svg tripwire: the drawn command line pins the clock with --today"):
        return
    check("%%" not in text, "svg tripwire: no doubled percent sign in assets/icm-check.svg")
    code, out, err = run_checker('example-broken', '--today', TODAY)
    live = [line for line in out.splitlines() if line.startswith(("[FAIL] ", "[WARN] "))]
    drawn = [s for s in spans if s.startswith(("[FAIL] ", "[WARN] "))]
    check(drawn == live, f"svg tripwire: the {len(drawn)} [FAIL]/[WARN] lines drawn equal the live output ({len(live)} lines)")
    m = summary(out)
    live_counts = f"{m.group(1)} FAIL / {m.group(2)} WARN" if m else None
    drawn_counts = None
    for s in spans:
        cm = re.match(r"\d+ FAIL / \d+ WARN", s)
        if cm:
            drawn_counts = cm.group(0)
    check(live_counts is not None and drawn_counts == live_counts,
          f"svg tripwire: drawn counts {drawn_counts!r} equal live counts {live_counts!r}")


# --- (j) banned phrases ------------------------------------------------------

def test_banned_phrases():
    hits, scanned = [], 0
    for entry in SWEEP:
        p = ROOT / entry
        if not check(p.exists(), f"banned-phrase sweep: {entry} present"):
            continue
        files = [p] if p.is_file() else sorted(
            f for f in p.rglob("*") if f.is_file() and not (SKIP_DIRS & set(f.relative_to(ROOT).parts)))
        for f in files:
            scanned += 1
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                m = BANNED.search(line)
                if m:
                    hits.append(f"{f.relative_to(ROOT).as_posix()}:{n}: {m.group(0)!r}")
    for h in hits:
        print(f"       banned: {h}")
    check(not hits, f"banned-phrase sweep: zero hits across {scanned} files ({len(hits)} found)")


# --- (k) robustness on scratch copies of example/ ---------------------------

class Scratch:
    """A throwaway copy of example/ to break on purpose."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="icm-ops-test-")
        self.root = pathlib.Path(self.tmp.name) / "ws"
        shutil.copytree(str(ROOT / "example"), str(self.root))

    def edit(self, rel, old, new):
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        if old not in text:
            raise AssertionError(f"{rel}: fixture text not found: {old!r}")
        p.write_bytes(text.replace(old, new, 1).encode("utf-8"))

    def write(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def run(self, *args):
        return run_checker(str(self.root), '--today', TODAY, *args)

    def close(self):
        self.tmp.cleanup()


LEDGER = "04-memory/ledger/2026-09.md"
DECISION = "01-context/decisions/0001-log-before-advising.md"
BRIEFING = "04-memory/ledger/BRIEFING.md"
json_results = []


def robust(number, name, prepare, judge):
    """One scratch case. prepare(ws) breaks the copy; judge(code, out)
    returns (condition, label) pairs. Every case also asserts empty stderr,
    a summary line, and a --json run that parses with the three keys."""
    base = f"robustness {number} ({name})"
    ws = Scratch()
    try:
        prepare(ws)
        code, out, err = ws.run()
        check(not err.strip() and summary(out) is not None,
              f"{base}: empty stderr and a summary line (exit {code}){stderr_note(err)}")
        for cond, label in judge(code, out):
            check(cond, f"{base}: {label}")
        jcode, jout, jerr = ws.run('--json')
        try:
            data = json.loads(jout)
        except ValueError:
            data = None
        json_results.append(isinstance(data, dict) and {"fail", "warn", "info"} <= set(data) and not jerr.strip())
    except Exception as e:  # noqa: BLE001 - a crash in the harness is a FAIL, not a stack trace
        check(False, f"{base}: raised {type(e).__name__}: {e}")
    finally:
        ws.close()


def test_robustness():
    if not CHECKER.is_file():
        return

    def malformed_dates(ws):
        ws.edit(LEDGER, "REVIEW-BY: 2026-12-31", "REVIEW-BY: 2026-02-30")
        ws.edit(DECISION, "review-by: 2027-09-08", "review-by: 2027-13-01")
        ws.edit(LEDGER, "## Readout — 2026-09-08", "## Readout — 2026-09-31")
        ws.edit("04-memory/STATE.md", "checked: 2026-09-08 ·", "checked: 2026-99-08 ·")
        ws.edit(BRIEFING, "readout: 2026-09-08", "readout: 2026-09-99")
        ws.edit("02-processes/one-process.md", "updated: 2026-09-08", "updated: 20260908")

    robust(1, "malformed dates at six sites", malformed_dates, lambda code, out: [
        (code == 0, "exit 0: a malformed date is a WARN, never a crash or a FAIL"),
        ("malformed `updated:` in 02-processes/one-process.md: '20260908'" in out, "frontmatter updated: reported"),
        ("malformed date in 01-context/decisions/0001-log-before-advising.md: '2027-13-01'" in out,
         "decision review-by reported"),
        ("readout heading without a parseable date in 2026-09.md" in out, "readout heading reported"),
        ("malformed date in 04-memory/ledger/2026-09.md: '2026-02-30'" in out, "REVIEW-BY reported"),
        ("malformed date in 04-memory/STATE.md: '2026-99-08'" in out, "checked stamp reported"),
        ("malformed date in 04-memory/ledger/BRIEFING.md: '2026-09-99'" in out, "BRIEFING readout: reported"),
        (out.count("[WARN] malformed") == 5 and out.count("without a parseable date") == 1,
         "exactly one finding per site"),
        ("readouts found: 0" in out, "the staleness check reports that it switched itself off"),
    ])

    def ids_and_keys(ws):
        ws.edit(LEDGER, "REVIEW-BY: 2026-12-31\nOUTCOME: open", "REVIEW-BY: 2026-08-01\noutcome: Open")
        text = (ws.root / LEDGER).read_text(encoding="utf-8")
        text += ("\n## L-1009 · 2026-09-01 · builder\nCLAIM: x\nCONFIDENCE: low\nFALSIFIER: y\n"
                 "COST: cheap\nREVIEW-BY: 2026-08-01\nOUTCOME: open\n"
                 "\n## L-08 · 2026-09-01 · builder\nCLAIM: x\nCONFIDENCE: low\nFALSIFIER: y\n"
                 "COST: cheap\nREVIEW-BY: 2027-08-01\nOUTCOME: open\n")
        ws.write(LEDGER, text)

    robust(2, "ids and case-insensitive keys", ids_and_keys, lambda code, out: [
        ("ledger L-005 past its date (2026-08-01)" in out, "expiry fires on `outcome: Open`"),
        ("ledger L-1009 past its date" in out, "a four-digit id is reported in full"),
        ("ledger id not zero-padded to three digits: L-08" in out, "L-08 reported as not zero-padded"),
    ])

    robust(3, "loose readout heading", lambda ws: ws.edit(LEDGER, "## Readout — 2026-09-08", "## Readout · 2026-09-08"),
           lambda code, out: [
               ("readouts found: 1 (newest 2026-09-08)" in out, "the readout is still counted"),
               (code == 0 and "[FAIL] BRIEFING.md" not in out and "[WARN] BRIEFING.md" not in out,
                "BRIEFING.md is still compared and still fresh"),
           ])

    robust(4, "unterminated frontmatter",
           lambda ws: ws.write("02-processes/dangling.md",
                               "---\ntype: process\nupdated: 2026-09-08\n\n# Dangling\n\nNo closing fence.\n"),
           lambda code, out: [
               ("[WARN] unterminated frontmatter: 02-processes/dangling.md" in out, "reported as unterminated"),
               ("frontmatter without `updated:` in 02-processes/dangling.md" not in out,
                "updated: is still found in the fallback"),
           ])

    def links(ws):
        ws.write("02-processes/one process.md", "---\ntype: process\nupdated: 2026-09-08\n---\n\n# Space\n")
        ws.write("02-processes/links.md",
                 "---\ntype: process\nupdated: 2026-09-08\n---\n\n# Links\n\n"
                 "[t](does-not-exist.md \"title\") [a](<one-process.md>) [e](one%20process.md)\n\n"
                 "```\n[f](fenced-missing.md)\n```\n\n[x](/etc/x.md) [h](https://example.org/x) [frag](#top)\n\n"
                 "`[c](inline-missing.md)` and ``[d](double-missing.md)``\n\n"
                 "    [i](indented-missing.md)\n\n"
                 "[r][ref] [ok][ref-ok]\n\n[ref]: ref-missing.md\n[ref-ok]: one-process.md \"title\"\n"
                 "[^1]: a footnote is not a link\n")

    def judge_links(code, out):
        broken = [line for line in out.splitlines() if line.startswith("[FAIL] broken relative link")]
        return [
            (len(broken) == 2 and any("does-not-exist.md" in b for b in broken)
             and any("ref-missing.md" in b for b in broken),
             "the missing inline target and the missing reference definition FAIL, nothing else"),
            (not any(s in out for s in ("fenced-missing", "inline-missing", "double-missing", "indented-missing")),
             "links inside fenced, inline and indented code are not scanned"),
            ("[INFO] absolute link left unchecked in 02-processes/links.md: (/etc/x.md)" in out,
             "an absolute link is INFO, not FAIL"),
        ]

    robust(5, "CommonMark link forms", links, judge_links)

    robust(6, "BOM in icm-ops.json",
           lambda ws: ws.write("icm-ops.json", b"\xef\xbb\xbf" + (ws.root / "icm-ops.json").read_bytes()),
           lambda code, out: [(code == 0 and "(config: icm-ops.json)" in out, "accepted and used")])

    def dirs_named_like_files(ws):
        (ws.root / "01-context" / "decisions" / "0009-dir.md").mkdir()
        (ws.root / "04-memory" / "ledger" / "2026-10.md").mkdir()

    robust(7, "directories named like a decision and a ledger month", dirs_named_like_files,
           lambda code, out: [(code == 0, "exit 0, both directories ignored")])

    def review_by_edges(ws):
        ws.edit(DECISION, "review-by: 2027-09-08", "review-by: 08/09/2027")
        ws.write("01-context/decisions/0002-body-only.md",
                 "---\ntype: decision\nstatus: accepted\nupdated: 2026-09-08\n---\n\n# 0002\n\n"
                 "review-by: 2027-09-08 sits in the body, which is prose.\n")

    robust(8, "review-by edge cases", review_by_edges, lambda code, out: [
        ("malformed date in 01-context/decisions/0001-log-before-advising.md: '08/09/2027'" in out,
         "a slashed date is malformed"),
        ("decision without review-by date: 0002-body-only.md" in out, "a body-only review-by does not count"),
    ])

    def drop_fields(ws):
        ws.edit(LEDGER, "CONFIDENCE: high\nFALSIFIER: the flag", "FALSIFIER: the flag")
        ws.edit(LEDGER, "COST: hours (a rollback under load); money if retries double-charge.\n", "")

    robust(9, "an entry missing field lines", drop_fields, lambda code, out: [
        (code == 0 and "[WARN] ledger L-001 lacks CONFIDENCE line" in out and "[WARN] ledger L-001 lacks COST line" in out,
         "L-001 without CONFIDENCE and COST is one WARN per field, exit 0"),
        (out.count(" lacks ") == 2, "no other entry lacks a field"),
    ])

    robust(10, "a hot_budgets key naming no walked file",
           lambda ws: ws.write("icm-ops.json", json.dumps({"hot_budgets": {"04-memory/STATE.md": 250, "04-memory/sate.md": 5}})),
           lambda code, out: [
               (code == 0 and "[WARN] hot_budgets names no markdown file the walk found: 04-memory/sate.md" in out,
                "the typo is a WARN, exit 0"),
               (re.search(r"^\[INFO\] 04-memory/STATE\.md: \d+/250 lines", out, re.M) is not None,
                "the key that names a file still reports"),
           ])

    robust(11, "the catalog over its hot budget",
           lambda ws: ws.write("icm-ops.json", json.dumps({"hot_budgets": {"00-catalog/CATALOG.md": 10}})),
           lambda code, out: [
               (code == 1 and out.count("[FAIL]") == 1 and "OVER its binding budget of 10" in out,
                "one defect, one FAIL: the binding budget, not the catalog's own rule as well"),
           ])

    robust(12, "a stray file in the ledger folder",
           lambda ws: ws.write("04-memory/ledger/2026-9.md",
                               "---\ntype: memory\nupdated: 2026-09-08\n---\n\n## L-099 · 2026-01-01 · builder\n"
                               "CLAIM: x\nCONFIDENCE: low\nFALSIFIER: y\nCOST: cheap\nREVIEW-BY: 2020-01-01\nOUTCOME: open\n"),
           lambda code, out: [
               ("not read as a ledger: 04-memory/ledger/2026-9.md" in out, "2026-9.md is reported as not a month file"),
               ("L-099" not in out, "its entries are not read"),
           ])

    def small_fixes(ws):
        ws.write("02-processes/UPPER.MD", "no frontmatter\n")
        ws.write("02-processes/rule.md", "----\n\nupdated: 2026-09-08\n")
        ws.edit("00-catalog/CATALOG.md", "| `04-memory/STATE.md` |", "| `04-memory//STATE.md` / `04-memory/./STATE.md` |")
        ws.write("04-memory/log/2026-09-09.md", "---\ntype: memory\nupdated: 2026-09-09\n---\n")
        ws.write("02-processes/crlf.md", b"---\r\ntype: process\r\nupdated: 2026-09-08\r\n---\r\n\r\n"
                                         b"checked: 2020-01-01 \xc2\xb7 vendor\r\n\r\nstale after: 30 days\r\n")

    robust(13, "an .MD extension, a ---- rule, doubled slashes, a log a day ahead, a CRLF stamp", small_fixes,
           lambda code, out: [
               ("[WARN] missing frontmatter: 02-processes/UPPER.MD" in out, "an .MD file is walked"),
               ("[WARN] missing frontmatter: 02-processes/rule.md" in out and "unterminated frontmatter" not in out,
                "a ---- rule is not a frontmatter opener"),
               ("catalog row points at missing path" not in out, "// and /./ in a catalog row resolve"),
               (code == 0 and "newest log is 2026-09-09 (1 day(s) ahead)" in out,
                "a log one day ahead is an INFO saying so, exit 0"),
               ("STALE ANCHOR" not in out, "a stamp wrapped across a CRLF blank line is not a stamp"),
           ])

    robust(16, "one ledger id on two entries, as two sessions numbering at once",
           lambda ws: ws.write("04-memory/ledger/2026-10.md",
                               "---\ntype: memory\nupdated: 2026-10-01\n---\n\n## L-006 · 2026-10-01 · builder\n"
                               "CLAIM: x\nCONFIDENCE: low\nFALSIFIER: y\nCOST: cheap\nREVIEW-BY: 2026-12-31\nOUTCOME: open\n"),
           lambda code, out: [
               (code == 0 and "[WARN] ledger id L-006 used 2 times (2026-09.md, 2026-10.md)" in out,
                "the reused id is a WARN naming both month files, exit 0"),
               (out.count("used 2 times") == 1, "reported once, not once per use"),
           ])

    def stray_logs(ws):
        ws.write("04-memory/log/2026-12-25.md", "---\ntype: memory\nupdated: 2026-12-25\n---\n")
        ws.write("04-memory/log/2026-xx-yy.md", "---\ntype: memory\nupdated: 2026-09-01\n---\n")
        ws.write("04-memory/log/2026-09-31.md", "---\ntype: memory\nupdated: 2026-09-01\n---\n")

    robust(17, "a future log beside a placeholder name and a date that is no real day", stray_logs,
           lambda code, out: [
               (code == 1 and "[FAIL] newest log 2026-12-25 is dated ahead" in out,
                "the newest real log is still judged against the clock (FAIL)"),
               ("[WARN] log has a non-date name: 2026-09-31.md" in out, "a date-shaped name that is no real day is a WARN"),
               ("2026-xx-yy" not in out, "a name that is not date-shaped is not read as a log"),
           ])

    def stray_beside_truncated(ws):
        ws.write("04-memory/log/2026-09-08.md.bak", "x" * 2000 + "\n")
        ws.write("04-memory/log/2026-09-08.md", "---\ntype: memory\nupdated: 2026-09-08\n---\n")
        ws.write("04-memory/log/2026-ab-cd.md", "---\ntype: memory\nupdated: 2026-09-01\n---\n")

    robust(18, "a stray name in the log folder beside a truncated newest log", stray_beside_truncated,
           lambda code, out: [
               (code == 1 and "[FAIL] POSSIBLE TRUNCATION: 04-memory/log/2026-09-08.md" in out,
                "the truncation guard still covers the newest real log"),
           ])

    def stamps_in_a_row(ws):
        state = (ws.root / "04-memory" / "STATE.md").read_text(encoding="utf-8")
        ws.write("04-memory/STATE.md", state +
                 "\nPrice 19 (checked: 2026-09-01 on the invoice). Fee 5 (checked: 2020-01-01 · vendor page"
                 " · stale after: 30 days).\n"
                 "\n- Seats: 40 (checked: 2026-09-01, by hand)\n- Rent 7 (checked: 2020-02-01 · lease"
                 " · stale after: 30 days)\n"
                 "\nTax 3 (checked: 2020-03-01 · rate card, re-checked: by phone · stale after: 30 days)\n")

    robust(19, "a checked: with no window just before a stamp", stamps_in_a_row,
           lambda code, out: [
               ("STALE ANCHOR in 04-memory/STATE.md: checked 2020-01-01" in out,
                "a stale stamp on the same line as an earlier checked: is still read"),
               ("STALE ANCHOR in 04-memory/STATE.md: checked 2020-02-01" in out and "malformed date" not in out,
                "a stale stamp on the bullet after one is still read, and the earlier one is no malformed date"),
               ("STALE ANCHOR in 04-memory/STATE.md: checked 2020-03-01" in out,
                "a re-checked: inside a stamp's source does not cut the stamp off"),
           ])

    robust(20, "a D-entry past KNOW-BY and still open",
           lambda ws: ws.write("04-memory/ledger/2026-10.md",
                               "---\ntype: memory\nupdated: 2026-10-01\n---\n\n"
                               "## D-001 · 2026-08-01 · builder: ship vs advisor: wait\n"
                               "STAKES: a week either way.\nKNOW-BY: 2026-08-15 — the launch.\nRESOLVED: open\n"),
           lambda code, out: [
               ("[WARN] ledger D-001 past its date (2026-08-15) and still open" in out, "it is a WARN"),
               ("D-001 past its date (2026-08-15) and still open — flag it for the owner" in out
                and "D-001 past its date (2026-08-15) and still open — resolve or mark EXPIRED" not in out,
                "it says to flag it for the owner, not to mark it EXPIRED (FORMAT.md, Disagreement entries)"),
           ])

    check(json_results and all(json_results),
          f"robustness 14 (--json parses with fail / warn / info in every case): {sum(json_results)}/{len(json_results)}")

    ws = Scratch()
    try:
        code, out, err = run_checker("\\\\?\\" + str(ws.root), '--today', TODAY)
        check(code == 0 and out.startswith("icm_check ") and not err.strip(),
              f"robustness 15 (extended-length root prefix): stripped and run (exit {code}){stderr_note(err)}")
    finally:
        ws.close()


# --- (m) leases --------------------------------------------------------------

LEASE = ROOT / "skills" / "icm-maintain" / "scripts" / "lease.py"
LEASE_PLUGIN_COPY = ROOT / "plugins" / "session-leases" / "lease.py"


def run_lease(lease_dir, *args, session=""):
    env = dict(os.environ, ICM_LEASE_DIR=str(lease_dir), CLAUDE_CODE_SESSION_ID=session)
    r = subprocess.run([sys.executable, str(LEASE)] + list(args), capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def test_lease():
    if not check(LEASE.is_file(), "lease: skills/icm-maintain/scripts/lease.py present"):
        return
    check(LEASE_PLUGIN_COPY.is_file() and LEASE_PLUGIN_COPY.read_bytes() == LEASE.read_bytes(),
          "lease: plugins/session-leases/lease.py is byte-identical to the skill's copy")
    with tempfile.TemporaryDirectory(prefix="icm-ops-lease-") as d:
        def held(name):
            return json.loads((pathlib.Path(d) / (name + ".json")).read_text(encoding="utf-8"))

        code, _ = run_lease(d, "take", "editor", "--who", "Docs", "--why", "build 80", "--minutes", "90", session="sess-a")
        check(code == 0, "lease: a free resource is taken (exit 0)")
        code, out = run_lease(d, "take", "editor", "--who", "Other", "--why", "build 81", session="sess-b")
        check(code == 1 and out.startswith("HELD:") and "Docs" in out,
              "lease: another session is refused (exit 1) and told who holds it")
        before = held("editor")
        code, out = run_lease(d, "take", "editor", "--why", "auto: build tool", "--minutes", "15", session="sess-a")
        after = held("editor")
        check(code == 0 and out.startswith("renewed") and after["who"] == "Docs" and after["why"] == "build 80"
              and after["expires"] >= before["expires"] and after["since"] == before["since"],
              "lease: the holder's own auto-claim renews, keeps the name and reason, never shortens")
        code, out = run_lease(d, "take", "editor", "--who", "Docs 2", "--why", "build 80", session="sess-a")
        check(code == 0 and out.startswith("renewed") and held("editor")["who"] == "Docs 2",
              "lease: a renewal with a new --who takes that name")
        run_lease(d, "take", "editor", "--who", "Docs", "--why", "build 80", session="sess-a")
        check(run_lease(d, "release", "editor", session="sess-b")[0] == 1,
              "lease: another session cannot release it")
        check(run_lease(d, "release", "editor", session="sess-a")[0] == 0 and run_lease(d, "check", "editor")[0] == 0,
              "lease: the holder releases it, and it reads free")
        (pathlib.Path(d) / "gpu.json").write_text(json.dumps(
            {"who": "Gone", "why": "crashed", "since": 0, "expires": 1, "session": "sess-c"}), encoding="utf-8")
        code, out = run_lease(d, "take", "gpu", "--why", "render", session="sess-b")
        kept = list((pathlib.Path(d) / "stale").glob("gpu-*.json"))
        check(code == 0 and "broke an expired lease" in out and len(kept) == 1,
              "lease: an expired lease is broken by the next taker and kept in stale/")
        log = (pathlib.Path(d) / "history.log").read_text(encoding="utf-8")
        check(all(w in log for w in ("TAKE editor", "RENEW editor", "RELEASE editor", "BREAK gpu")),
              "lease: history.log records take, renew, release and break")
        check(run_lease(d, "take", "Bad Name", "--who", "x", "--why", "y")[0] == 2
              and run_lease(d, "take", "gpu", "--who", "x", "--why", "y", "--minutes", "0")[0] == 2
              and run_lease(d, "take", "gpu", "--why", "y")[0] == 2,
              "lease: a bad name, bad minutes, or no name and no session is a usage error (exit 2)")
    with tempfile.TemporaryDirectory(prefix="icm-ops-lease-race-") as d:
        procs = [subprocess.Popen([sys.executable, str(LEASE), "take", "git-repo", "--why", "push"],
                                  env=dict(os.environ, ICM_LEASE_DIR=d, CLAUDE_CODE_SESSION_ID="racer-%d" % i),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for i in range(8)]
        codes = [p.wait() for p in procs]
        for p in procs:
            p.stdout.close()
            p.stderr.close()
        check(codes.count(0) == 1 and codes.count(1) == 7,
              f"lease: eight sessions taking at once, exactly one wins (exit codes {sorted(codes)})")
    test_lease_interleavings()
    test_lease_locks()
    test_lease_documented_lines()
    with tempfile.TemporaryDirectory(prefix="icm-ops-lease-home-") as d:
        base = pathlib.Path(d)
        env = {k: v for k, v in os.environ.items() if k not in ("ICM_LEASE_DIR", "XDG_STATE_HOME")}
        env.update(USERPROFILE=str(base / "profile"), LOCALAPPDATA=str(base / "appdata"), HOME=str(base / "home"),
                   XDG_STATE_HOME=str(base / "state"), CLAUDE_CODE_SESSION_ID="sess-home")
        r = subprocess.run([sys.executable, str(LEASE), "take", "editor", "--why", "where"],
                           capture_output=True, text=True, env=env)
        want = base / "profile" / ".icm-leases" if os.name == "nt" else base / "state" / "icm-leases"
        found = sorted(base.rglob("editor.json"))
        check(r.returncode == 0 and found == [want / "editor.json"],
              "lease: with ICM_LEASE_DIR unset the folder is <profile>/.icm-leases on Windows, never AppData, "
              f"and $XDG_STATE_HOME/icm-leases elsewhere (found {[str(p.relative_to(base)) for p in found]})")


# Session A runs lease.py in-process; the moment A has read the lease file, session B (a real
# second process) takes the same resource, and A goes on once B is done or 1 s has passed. That
# is the window in which two sessions can each be told they hold one resource.
INTERLEAVE = r'''
import importlib.util, json, os, subprocess, sys
spec = importlib.util.spec_from_file_location("lease", sys.argv[1])
lease = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lease)
plain, b = lease.read, []
def read(p):
    cur = plain(p)
    if not b:
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID="sess-b")
        b.append(subprocess.Popen([sys.executable, sys.argv[1], "take", "gpu", "--why", "b"], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        try:
            b[0].wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass  # B is waiting on A, as it should
    return cur
lease.read = read
os.environ["CLAUDE_CODE_SESSION_ID"] = "sess-a"
code_a = lease.main(sys.argv[2:])
print(json.dumps([code_a, b[0].wait() if b else None]))
'''


def test_lease_interleavings():
    with tempfile.TemporaryDirectory(prefix="icm-ops-lease-weave-") as d:
        harness = pathlib.Path(d) / "interleave.py"
        harness.write_text(INTERLEAVE, encoding="utf-8")
        leases = pathlib.Path(d) / "leases"
        leases.mkdir()
        env = dict(os.environ, ICM_LEASE_DIR=str(leases))

        def weave(seed, *a_args):
            for p in leases.glob("**/*"):
                if p.is_file():
                    p.unlink()
            (leases / "gpu.json").write_text(json.dumps(seed), encoding="utf-8")
            r = subprocess.run([sys.executable, "-I", str(harness), str(LEASE)] + list(a_args),
                               capture_output=True, text=True, env=env, timeout=60)
            codes = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else None
            gpu = leases / "gpu.json"
            holder = json.loads(gpu.read_text(encoding="utf-8")).get("session") if gpu.exists() else None
            return codes, holder

        old = {"who": "Gone", "why": "crashed", "since": 0, "expires": 1, "session": "sess-old"}
        codes, holder = weave(old, "take", "gpu", "--why", "a")
        check(codes is not None and codes.count(0) == 1 and holder in ("sess-a", "sess-b")
              and holder == ("sess-a", "sess-b")[codes.index(0)],
              f"lease: two sessions breaking one expired lease at once, exactly one is told it took it "
              f"and it is the one on file (exit codes A, B: {codes}; on file: {holder})")
        mine = {"who": "session sess-a", "why": "a", "since": 0, "expires": 1, "session": "sess-a"}
        codes, holder = weave(mine, "release", "gpu")
        check(codes == [0, 0] and holder == "sess-b",
              f"lease: a release never removes the lease another session took meanwhile "
              f"(exit codes A, B: {codes}; on file: {holder})")
        codes, holder = weave(mine, "take", "gpu", "--why", "a")
        check(codes is not None and codes.count(0) == 1 and holder == ("sess-a", "sess-b")[codes.index(0)],
              f"lease: a holder renewing its expired lease while another session takes it leaves one holder, "
              f"the one on file (exit codes A, B: {codes}; on file: {holder})")


# A lease.py run in-process with its lock wait cut to 1 s, so a lock that never goes is quick to test.
SHORT_WAIT = r'''
import importlib.util, sys
spec = importlib.util.spec_from_file_location("lease", sys.argv[1])
lease = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lease)
lease.LOCK_WAIT = 1
sys.exit(lease.main(sys.argv[2:]))
'''


def test_lease_locks():
    with tempfile.TemporaryDirectory(prefix="icm-ops-lease-lock-") as d:
        leases = pathlib.Path(d) / "leases"
        leases.mkdir()
        env = dict(os.environ, ICM_LEASE_DIR=str(leases), CLAUDE_CODE_SESSION_ID="sess-a")
        old = json.dumps({"who": "Gone", "why": "crashed", "since": 0, "expires": 1, "session": "sess-old"})
        (leases / "gpu.json").write_text(old, encoding="utf-8")
        lock = leases / "gpu.json.lock"
        lock.write_text("", encoding="utf-8")
        hour_ago = time.time() - 3600
        os.utime(str(lock), (hour_ago, hour_ago))
        try:
            r = subprocess.run([sys.executable, str(LEASE), "take", "gpu", "--why", "a"],
                               capture_output=True, text=True, env=env, timeout=20)
            ok = r.returncode == 0 and r.stdout.strip().splitlines()[-1].startswith("took gpu") and not lock.exists()
        except subprocess.TimeoutExpired:
            ok = False
        check(ok, "lease: a change lock left by a dead process is removed, and the take goes ahead")
        (leases / "gpu.json").write_text(old, encoding="utf-8")
        if lock.is_file():
            lock.unlink()  # left by the case above when it failed
        lock.mkdir()  # a lock that cannot be removed
        os.utime(str(lock), (hour_ago, hour_ago))
        harness = pathlib.Path(d) / "short_wait.py"
        harness.write_text(SHORT_WAIT, encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, "-I", str(harness), str(LEASE), "take", "gpu", "--why", "a"],
                               capture_output=True, text=True, env=env, timeout=20)
            ok = (r.returncode == 1 and "could not lock gpu" in r.stderr
                  and (leases / "gpu.json").read_text(encoding="utf-8") == old)
        except subprocess.TimeoutExpired:
            ok = False
        check(ok, "lease: a lock that cannot be removed ends in exit 1 and a message, the lease untouched, "
                  "never an endless wait")


def test_lease_documented_lines():
    """Every `python lease.py ...` line the docs show runs as written outside a session."""
    lines = []
    for doc in (LEASE, ROOT / "skills" / "icm-maintain" / "references" / "sessions.md"):
        for line in doc.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("python lease.py "):
                lines.append(line.strip()[len("python lease.py "):].replace("<your session's name>", "docs session"))
    with tempfile.TemporaryDirectory(prefix="icm-ops-lease-docs-") as d:
        bad = []
        for line in lines:
            code, out = run_lease(d, *shlex.split(line))
            if code == 2 or (line.startswith("release") and "released" not in out):
                bad.append("%s -> exit %d: %s" % (line, code, out.strip()[:80]))
        check(len(lines) >= 8 and not bad and run_lease(d, "check", "editor")[0] == 0,
              f"lease: the {len(lines)} documented command lines run as written outside a session {bad}")
        cfg = pathlib.Path(d) / "config.json"
        cfg.write_text('{"python": "python3"}', encoding="utf-8")
        code, _ = run_lease(d, "take", "config", "--who", "x", "--why", "y")
        check(code == 2 and cfg.read_text(encoding="utf-8") == '{"python": "python3"}',
              "lease: 'config' is refused as a resource name and the machine config.json is left alone")


# --- (l) config errors exit 2 -----------------------------------------------

def test_config_errors():
    if not CHECKER.is_file():
        return
    cases = [
        ("an absolute catalog path", {"catalog": "/abs/CATALOG.md"}),
        ("a .. segment in ledger_dir", {"ledger_dir": "../ledger"}),
        ("an absolute hot_budgets key", {"hot_budgets": {"/etc/STATE.md": 5}}),
        ("an empty hot_budgets key", {"hot_budgets": {"": 5}}),
    ]
    for label, cfg in cases:
        ws = Scratch()
        try:
            ws.write("icm-ops.json", json.dumps(cfg))
            code, out, err = ws.run()
            check(code == 2 and out == "" and err.strip() != "",
                  f"config error exits 2 with nothing on stdout: {label} (got {code})")
        finally:
            ws.close()
    ws = Scratch()
    try:
        (ws.root / "icm-ops.json").unlink()
        (ws.root / "icm-ops.json").mkdir()
        code, out, err = ws.run()
        check(code == 2 and out == "" and err.strip() != "",
              f"config error exits 2 with nothing on stdout: icm-ops.json is a directory (got {code})")
    finally:
        ws.close()


def main():
    print(f"icm-ops tests — repo {ROOT}\n")
    test_skill_frontmatter()
    test_example_clean()
    test_example_broken()
    test_json()
    test_future_clock()
    test_usage_errors()
    test_internal_error()
    test_version_sync()
    test_line_endings()
    test_svg_tripwire()
    test_banned_phrases()
    test_robustness()
    test_config_errors()
    test_lease()
    print(f"\n{counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['SKIP']} SKIP")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    sys.exit(main())
