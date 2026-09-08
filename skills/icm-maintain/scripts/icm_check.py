#!/usr/bin/env python3
"""icm_check.py -- integrity checker for an ICM workspace. Read-only.

Usage:
    python icm_check.py [workspace-root] [--json] [--config PATH]

Audits the workspace as a system:
  1.  Every catalog row points at a file or folder that exists.
  2.  Every markdown file is reachable from the catalog (own row, or an
      ancestor-folder row).
  3.  Every relative markdown link resolves.
  4.  Frontmatter is present and carries a well-formed `updated:` date.
  5.  File sizes: hot files carry BINDING budgets (over = FAIL). Other
      working files WARN past the size target and FAIL past twice it.
      Historical records (daily logs, monthly ledgers, deliverables)
      only ever WARN.
  6.  The catalog against its own line rule.
  7.  Decision records carry `review-by:` dates, and none is due.
  7b. Ledger entries past REVIEW-BY / KNOW-BY and still open.
  7c. `checked: DATE . source . stale after: N days` stamps whose window
      has blown.
  7d. BRIEFING.md older than the newest ledger readout.
  8.  Clock vs the newest daily log (a log dated in the future FAILS).
  9.  Protected files that collapsed below 40% of their .bak copy
      (possible truncation). The checker DETECTS; the maintenance
      process is what writes the .bak files, and only after a clean run.

Reports, never fixes. Exit 0 with no FAIL, 1 with any FAIL, 2 on a usage
or config error. `--json` prints {"fail": [...], "warn": [...], "info": [...]}
to stdout and nothing else.

Configuration: an optional `icm-ops.json` at the workspace root (or the
file named by --config). Every key is optional; defaults are the ICM
conventions. Paths are relative to the workspace root, forward slashes.

    {
      "hot_budgets":        {"04-memory/STATE.md": 250, ...},   binding line budgets
      "protected":          ["CLAUDE.md", ...],                 truncation-guarded files
      "deliverable_markers":["/product/"],                      path substrings exempt
                                                                from size, orphan and
                                                                frontmatter rules
      "frontmatter_exempt": ["CLAUDE.md", "AGENTS.md", "README.md"],  root files
      "size_target_lines":  200,
      "historical_dirs":    ["04-memory/log/"],                 records, not working files
      "log_dir":            "04-memory/log",                    daily logs (clock check)
      "ledger_dir":         "04-memory/ledger",
      "decisions_dir":      "01-context/decisions",
      "catalog":            "00-catalog/CATALOG.md"
    }

Line counts use wc -l semantics: newline-terminated lines plus a final
unterminated one. This script owns that definition, because it fails
the build on it.

Python 3 standard library only. Windows-safe: every file is read as UTF-8
and stdout is switched to UTF-8 before anything is printed.
"""
import datetime
import json
import os
import pathlib
import re
import sys

DEFAULTS = {
    "hot_budgets": {
        "04-memory/STATE.md": 250,
        "00-catalog/CATALOG.md": 155,
        "04-memory/maintenance-log.md": 60,
    },
    "protected": [
        "CLAUDE.md", "AGENTS.md",
        "00-catalog/CATALOG.md", "00-catalog/CONVENTIONS.md",
        "04-memory/STATE.md", "04-memory/ledger/BRIEFING.md",
        "04-memory/maintenance-log.md",
    ],
    "deliverable_markers": [],
    "frontmatter_exempt": ["CLAUDE.md", "AGENTS.md", "README.md"],
    "size_target_lines": 200,
    "historical_dirs": ["04-memory/log/"],
    "log_dir": "04-memory/log",
    "ledger_dir": "04-memory/ledger",
    "decisions_dir": "01-context/decisions",
    "catalog": "00-catalog/CATALOG.md",
}
LIST_KEYS = ("protected", "deliverable_markers", "frontmatter_exempt", "historical_dirs")
STR_KEYS = ("log_dir", "ledger_dir", "decisions_dir", "catalog")
SKIP_DIRS = {"node_modules", "__pycache__"}
DATE = r"(\d{4}-\d{2}-\d{2})"
USAGE = "usage: python icm_check.py [workspace-root] [--json] [--config PATH]"


def die(msg, code=2):
    print(f"icm_check: {msg}", file=sys.stderr)
    if code == 2:
        print(USAGE, file=sys.stderr)
    sys.exit(code)


def parse_args(argv):
    root, as_json, config = None, False, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        elif a == "--json":
            as_json = True
        elif a == "--config":
            if i + 1 >= len(argv):
                die("--config needs a path")
            config = argv[i + 1]
            i += 1
        elif a.startswith("--config="):
            config = a.split("=", 1)[1]
        elif a.startswith("-"):
            die(f"unknown option: {a}")
        elif root is None:
            root = a
        else:
            die(f"unexpected argument: {a}")
        i += 1
    return root or ".", as_json, config


def norm(p):
    return str(p).replace("\\", "/").strip().strip("/")


def load_config(root, explicit):
    cfg = json.loads(json.dumps(DEFAULTS))
    path = pathlib.Path(explicit) if explicit else root / "icm-ops.json"
    if explicit and not path.is_file():
        die(f"config not found: {path}")
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            die(f"cannot read config {path}: {e}")
        if not isinstance(data, dict):
            die(f"config {path} must be a JSON object")
        for k, v in data.items():
            if k not in DEFAULTS:
                die(f"unknown config key {k!r} in {path}; known: {', '.join(DEFAULTS)}")
            if k == "hot_budgets":
                if not isinstance(v, dict) or not all(
                        isinstance(kk, str) and isinstance(vv, int) and not isinstance(vv, bool) and vv > 0
                        for kk, vv in v.items()):
                    die("config hot_budgets must map path -> positive integer")
                v = {norm(kk): vv for kk, vv in v.items()}
            elif k in LIST_KEYS:
                if not isinstance(v, list) or not all(isinstance(x, str) and x for x in v):
                    die(f"config {k} must be a list of non-empty strings")
            elif k == "size_target_lines":
                if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                    die("config size_target_lines must be a positive integer")
            elif k in STR_KEYS:
                if not isinstance(v, str) or not v.strip():
                    die(f"config {k} must be a non-empty string")
            cfg[k] = v
    for k in STR_KEYS:
        cfg[k] = norm(cfg[k])
    cfg["protected"] = [norm(p) for p in cfg["protected"]]
    cfg["historical_dirs"] = [norm(d) + "/" for d in cfg["historical_dirs"]]
    return cfg, (path if path.is_file() else None)


def count_lines(text):
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def md_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(".md"):
                out.append(pathlib.Path(dirpath) / fn)
    return sorted(out)


def run(root, cfg):
    findings = {"FAIL": [], "WARN": [], "INFO": []}

    def add(level, msg):
        findings[level].append(msg)

    today = datetime.date.today()
    catalog = root / cfg["catalog"]
    cat_text = read(catalog)
    markers = tuple(cfg["deliverable_markers"])
    hot = cfg["hot_budgets"]
    target = cfg["size_target_lines"]
    split_at = target * 2
    ledger_dir = root / cfg["ledger_dir"]
    decisions_dir = root / cfg["decisions_dir"]
    log_dir = root / cfg["log_dir"]
    frontmatter_exempt = set(cfg["frontmatter_exempt"])
    month_re = re.compile(re.escape(cfg["ledger_dir"]) + r"/2\d{3}-\d{2}\.md")

    def is_deliverable(rel):
        return any(m in "/" + rel + "/" for m in markers)

    def is_historical(rel):
        return (rel.startswith(tuple(cfg["historical_dirs"])) or is_deliverable(rel)
                or month_re.fullmatch(rel) is not None)

    files = md_files(root)
    rels = {f: f.relative_to(root).as_posix() for f in files}

    # --- 1. catalog rows -> existing paths ---------------------------------
    # A row's path cell may hold one path or several joined by " / "
    # (`CLAUDE.md` / `AGENTS.md`), each in backticks.
    covered_prefixes = []
    for m in re.finditer(r"^\|([^|\n]*)\|", cat_text, re.M):
        for span in re.findall(r"`([^`]+)`", m.group(1)):
            for p in re.split(r"\s+/\s+", span.strip()):
                rel = norm(p)
                if not rel:
                    continue
                if not (root / rel).exists():
                    add("FAIL", f"catalog row points at missing path: {p}")
                covered_prefixes.append(rel)

    # --- 2. orphan files (no row, no ancestor-folder row) ------------------
    def covered(rel):
        return any(rel == c or rel.startswith(c + "/") for c in covered_prefixes)

    catalog_dir = cfg["catalog"].rsplit("/", 1)[0] + "/" if "/" in cfg["catalog"] else None
    for f in files:
        rel = rels[f]
        if catalog_dir and rel.startswith(catalog_dir):
            continue
        if f.name in frontmatter_exempt and "/" not in rel:
            continue
        if f.name == "_TEMPLATE.md" or rel.endswith("README.md") or is_deliverable(rel):
            continue  # templates, readmes and deliverable content ride with their folder
        if not covered(rel):
            add("WARN", f"no catalog coverage (own row or ancestor folder row): {rel}")

    # --- 3. relative links resolve -----------------------------------------
    link_re = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
    for f in files:
        for m in link_re.finditer(read(f)):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:")) or "://" in href:
                continue
            if not (f.parent / href).exists():
                add("FAIL", f"broken relative link in {rels[f]}: ({href})")

    # --- 4. frontmatter present, `updated:` well-formed --------------------
    for f in files:
        rel = rels[f]
        if (f.name in frontmatter_exempt and "/" not in rel) or is_deliverable(rel):
            continue
        text = read(f).lstrip("﻿ \t\r\n")
        if not text.startswith("---"):
            add("WARN", f"missing frontmatter: {rel}")
            continue
        if f.name == "_TEMPLATE.md":
            continue  # templates carry the placeholder YYYY-MM-DD on purpose
        end = text.find("\n---", 3)
        block = text[3:end] if end > 0 else text[3:600]
        m = re.search(r"^updated:\s*(.*?)\s*$", block, re.M)
        if not m:
            add("WARN", f"frontmatter without `updated:` in {rel}")
        else:
            try:
                datetime.date.fromisoformat(m.group(1))
            except ValueError:
                add("WARN", f"malformed `updated:` in {rel}: {m.group(1)!r} (want YYYY-MM-DD)")

    # --- 5. file sizes ------------------------------------------------------
    # Hot files carry BINDING budgets: over budget FAILS, because a WARN
    # that stays yellow for weeks becomes wallpaper. The fix is routine
    # compaction, not heroics.
    for f in files:
        rel = rels[f]
        n = count_lines(read(f))
        if rel in hot:
            if n > hot[rel]:
                add("FAIL", f"{rel}: {n} lines — OVER its binding budget of {hot[rel]}. "
                            "Run the compaction routine.")
            else:
                add("INFO", f"{rel}: {n}/{hot[rel]} lines (hot-file budget)")
            continue
        historical = is_historical(rel)
        if n > split_at:
            add("WARN" if historical else "FAIL",
                f"{rel}: {n} lines (convention: >{split_at} = doing two jobs"
                f"{' — historical record' if historical else ', split it'})")
        elif n > target and not historical:
            add("WARN", f"{rel}: {n} lines (target is under {target})")

    # --- 6. catalog's own line rule ----------------------------------------
    # Soft and hard lines follow the catalog's hot budget when it has one
    # (155 -> warn past 150, fail past 170), else the 150/170 convention.
    cat_lines = count_lines(cat_text)
    budget = hot.get(cfg["catalog"])
    soft, hard = (budget - 5, budget + 15) if budget else (150, 170)
    lvl = "FAIL" if cat_lines > hard else ("WARN" if cat_lines > soft else "INFO")
    add(lvl, f"{catalog.name} is {cat_lines} lines (its own rule: keep under ~{soft})")

    # --- 7. decisions carry review-by; 7a. none is due ---------------------
    decisions = sorted(decisions_dir.glob("[0-9]*.md")) if decisions_dir.is_dir() else []
    for f in decisions:
        head = read(f)[:400]
        m = re.search(r"^review-by:\s*" + DATE, head, re.M)
        if "review-by:" not in head:
            add("WARN", f"decision without review-by date: {f.name}")
        elif m and datetime.date.fromisoformat(m.group(1)) <= today:
            add("WARN", f"decision DUE FOR REVIEW: {f.name} (review-by {m.group(1)}) — reopen or renew the date")

    # --- 7b. ledger clocks: readouts, entries past their date still open ---
    newest_readout = None
    ledgers = sorted(ledger_dir.glob("2???-??.md")) if ledger_dir.is_dir() else []
    for f in ledgers:
        t = read(f)
        for m in re.finditer(r"^## Readout\s*[—–-]+\s*" + DATE, t, re.M):
            d = datetime.date.fromisoformat(m.group(1))
            newest_readout = max(newest_readout or d, d)
        for block in re.split(r"(?m)^## ", t):
            idm = re.match(r"([LD]-\d{3})", block)
            if not idm:
                continue
            due = re.search(r"(?:REVIEW-BY|KNOW-BY):\s*" + DATE, block)
            is_open = re.search(r"(?:OUTCOME|RESOLVED):\s*open", block)
            if due and is_open and datetime.date.fromisoformat(due.group(1)) < today:
                add("WARN", f"ledger {idm.group(1)} past its date ({due.group(1)}) and still open "
                            f"— resolve or mark EXPIRED ({f.name})")

    # --- 7c. checked-stamps: external numbers past their staleness window --
    # Convention: externally-sourced figures carry
    # "checked: YYYY-MM-DD · source · stale after: N days". A blown window
    # means the number describes the past while reading as the present.
    stamp = re.compile(r"checked:\s*" + DATE + r"(?:[^\n]|\n(?!\n)){0,120}?stale after:\s*(\d+)\s*day")
    for f in files:
        rel = rels[f]
        if is_historical(rel):
            continue
        for m in stamp.finditer(read(f)):
            checked = datetime.date.fromisoformat(m.group(1))
            blown = (today - checked).days - int(m.group(2))
            if blown > 0:
                add("WARN", f"STALE ANCHOR in {rel}: checked {m.group(1)}, window {m.group(2)}d blown by "
                            f"{blown}d — re-check at the source or remove the number")

    # --- 7d. briefing staleness: a stale correction wears a fresh voice ----
    bf = ledger_dir / "BRIEFING.md"
    if bf.exists() and newest_readout:
        m = re.search(r"^updated:\s*" + DATE, read(bf)[:200], re.M)
        if m and datetime.date.fromisoformat(m.group(1)) < newest_readout:
            add("FAIL", f"BRIEFING.md ({m.group(1)}) is OLDER than the newest ledger readout "
                        f"({newest_readout}) — regenerate it and the front-desk block")

    # --- 8. clock vs newest log (date tripwire) ----------------------------
    logs = sorted(log_dir.glob("2???-??-??.md")) if log_dir.is_dir() else []
    if logs:
        newest = logs[-1].stem
        try:
            age = (today - datetime.date.fromisoformat(newest)).days
        except ValueError:
            add("WARN", f"newest log has a non-date name: {newest}.md")
        else:
            add("INFO", f"clock says {today.isoformat()}; newest log is {newest} ({age} day(s) old)")
            if age < 0:
                add("FAIL", f"newest log {newest} is dated in the FUTURE — a date was written from a "
                            "stale or wrong clock")

    # --- 9. truncation guard -----------------------------------------------
    # A protected file must not collapse below 40% of its last-known-good
    # .bak. Recovery: copy <file>.bak back; never overwrite the .bak.
    protected = list(cfg["protected"])
    if ledgers:
        protected.append(ledgers[-1].relative_to(root).as_posix())
    if logs:
        protected.append(logs[-1].relative_to(root).as_posix())
    for rel in protected:
        f, bak = root / rel, root / (rel + ".bak")
        if not f.exists():
            continue
        if bak.exists():
            cur, prev = f.stat().st_size, bak.stat().st_size
            if prev > 400 and cur < 0.4 * prev:
                add("FAIL", f"POSSIBLE TRUNCATION: {rel} is {cur} bytes vs backup {prev} — recover from "
                            f"{rel}.bak; do NOT overwrite the .bak")
        else:
            add("INFO", f"no .bak yet for protected file {rel} — next maintenance run creates it")

    return findings


def main(argv):
    root_arg, as_json, config_arg = parse_args(argv)
    root = pathlib.Path(root_arg).resolve()
    if not root.is_dir():
        die(f"workspace root is not a directory: {root_arg}")
    cfg, cfg_path = load_config(root, config_arg)
    if not (root / cfg["catalog"]).is_file():
        die(f"catalog not found: {root / cfg['catalog']} (not an ICM workspace, or set \"catalog\" in icm-ops.json)")

    findings = run(root, cfg)

    if as_json:
        print(json.dumps({"fail": findings["FAIL"], "warn": findings["WARN"], "info": findings["INFO"]}, indent=2))
    else:
        where = f" (config: {cfg_path.name})" if cfg_path else " (defaults)"
        print(f"icm_check run {datetime.date.today().isoformat()} on {root.name}{where} "
              "— dates are claims; this line is the clock\n")
        for level in ("FAIL", "WARN", "INFO"):
            for msg in findings[level]:
                print(f"[{level}] {msg}")
        print(f"\n{len(findings['FAIL'])} FAIL / {len(findings['WARN'])} WARN / {len(findings['INFO'])} INFO")
    return 1 if findings["FAIL"] else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    sys.exit(main(sys.argv[1:]))
