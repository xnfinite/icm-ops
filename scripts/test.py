#!/usr/bin/env python3
"""icm-ops test runner. Standard library only. Run from anywhere:

    python scripts/test.py

Prints one [PASS] / [FAIL] / [SKIP] line per assertion and a summary; exits 1
on any FAIL. What it checks:

  (a) every skills/*/SKILL.md has spec-valid frontmatter: name equals the
      folder, matches ^[a-z0-9]+(-[a-z0-9]+)*$ and is at most 64 chars;
      description non-empty and at most 1024; license present.
      Missing SKILL.md files are SKIP, not FAIL, so parallel work streams
      can finish independently.
  (b) icm_check.py on example/ exits 0 with 0 FAIL.
  (c) icm_check.py on example-broken/ exits 1 and names all five seeded
      defects (see example-broken/README-BROKEN.md).
  (d) --json on example/ parses and carries the fail / warn / info keys.
  (e) a case-insensitive banned-phrase sweep over shipped files finds zero
      hits. Folders that do not exist yet are skipped.
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKER = ROOT / "skills" / "icm-maintain" / "scripts" / "icm_check.py"
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BANNED = re.compile(
    r"can.t hallucinate|cannot hallucinate|hallucination.free|unhackable|the only|"
    r"the first|the best|nobody else|upwork|etsy|fiverr|lizton|wickhouse|connects\b|"
    r"skool|reddit\.com", re.I)
SWEEP = ["README.md", "skills", "example", "example-broken", "plugins"]
SKIP_DIRS = {".git", "node_modules", "__pycache__"}

counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def report(status, msg):
    counts[status] += 1
    print(f"[{status}] {msg}")


def check(cond, msg):
    report("PASS" if cond else "FAIL", msg)
    return bool(cond)


def parse_frontmatter(text):
    """Minimal YAML-ish frontmatter reader: top-level `key: value` pairs.
    Continuation lines (folded scalars, nested maps) are appended to the
    previous key so presence and length can be judged."""
    text = text.lstrip("﻿")
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


def test_skill_frontmatter():
    skills_dir = ROOT / "skills"
    folders = sorted(p for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []
    expected = ["icm-ledger", "icm-verifier", "icm-maintain"]
    for name in expected:
        if not (skills_dir / name / "SKILL.md").is_file():
            report("SKIP", f"skills/{name}/SKILL.md not present yet")
    for folder in folders:
        skill = folder / "SKILL.md"
        if not skill.is_file():
            continue
        rel = f"skills/{folder.name}/SKILL.md"
        fm = parse_frontmatter(skill.read_text(encoding="utf-8", errors="replace"))
        if not check(fm is not None, f"{rel}: frontmatter block present"):
            continue
        name = fm.get("name", "")
        check(name == folder.name, f"{rel}: name {name!r} equals folder name")
        check(bool(SKILL_NAME.match(name)) and len(name) <= 64,
              f"{rel}: name matches ^[a-z0-9]+(-[a-z0-9]+)*$ and is <= 64 chars")
        desc = fm.get("description", "")
        check(0 < len(desc) <= 1024, f"{rel}: description non-empty and <= 1024 chars ({len(desc)})")
        check(bool(fm.get("license")), f"{rel}: license present")


def test_example_clean():
    if not check(CHECKER.is_file(), f"checker present at {CHECKER.relative_to(ROOT).as_posix()}"):
        return
    code, out, err = run_checker("example")
    check(code == 0, f"example/: exit code 0 (got {code}){(' stderr: ' + err.strip()) if err.strip() else ''}")
    check(re.search(r"^0 FAIL / \d+ WARN / \d+ INFO$", out, re.M) is not None,
          "example/: summary line reports 0 FAIL")


def test_example_broken():
    if not CHECKER.is_file():
        return
    code, out, err = run_checker("example-broken")
    check(code == 1, f"example-broken/: exit code 1 (got {code}){(' stderr: ' + err.strip()) if err.strip() else ''}")
    expectations = [
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
    for label, pattern in expectations:
        check(pattern.search(out) is not None, f"example-broken/: {label}")
    m = re.search(r"^(\d+) FAIL / (\d+) WARN / \d+ INFO$", out, re.M)
    check(m is not None and (int(m.group(1)), int(m.group(2))) == (3, 2),
          f"example-broken/: exactly 3 FAIL / 2 WARN (got {m.group(0) if m else 'no summary line'})")


def test_json():
    if not CHECKER.is_file():
        return
    code, out, err = run_checker("example", "--json")
    try:
        data = json.loads(out)
    except ValueError as e:
        check(False, f"example/ --json: stdout parses as JSON ({e})")
        return
    check(isinstance(data, dict) and set(data) == {"fail", "warn", "info"},
          f"example/ --json: keys are fail / warn / info (got {sorted(data) if isinstance(data, dict) else type(data).__name__})")
    check(all(isinstance(data.get(k), list) for k in ("fail", "warn", "info")),
          "example/ --json: every value is a list")
    check(data.get("fail") == [] and code == 0, "example/ --json: fail list empty and exit 0")


def test_banned_phrases():
    hits, scanned = [], 0
    for entry in SWEEP:
        p = ROOT / entry
        if not p.exists():
            report("SKIP", f"banned-phrase sweep: {entry} not present yet")
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


def main():
    print(f"icm-ops tests — repo {ROOT}\n")
    test_skill_frontmatter()
    test_example_clean()
    test_example_broken()
    test_json()
    test_banned_phrases()
    print(f"\n{counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['SKIP']} SKIP")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    sys.exit(main())
