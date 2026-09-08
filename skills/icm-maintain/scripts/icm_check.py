#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Nightflow Systems
"""icm_check.py -- integrity checker for an ICM workspace. Read-only.

Usage:
    python icm_check.py [workspace-root] [--json] [--config PATH]
                        [--today YYYY-MM-DD] [--version] [-h]

Audits the workspace as a system:
  1.  Every catalog row points at a file or folder that exists.
  2.  Every markdown file is reachable from the catalog (own row, or an
      ancestor-folder row).
  3.  Every relative markdown link resolves: inline links and
      reference-style definitions (`[label]: path`). Code is not scanned
      -- fenced blocks, inline code spans, and lines indented four spaces
      or a tab after a blank line; absolute links are left unchecked and
      listed as INFO.
  4.  Frontmatter is present, terminated, and carries a well-formed
      `updated:` date.
  5.  File sizes: hot files carry BINDING budgets (over = FAIL; a budget
      key that names no walked file is a WARN). Other working files WARN
      past the size target and FAIL past twice it. Historical records
      (daily logs, monthly ledgers, deliverables) only ever WARN.
  6.  The catalog against its own line rule.
  7.  Decision records carry `review-by:` dates, and none is due.
  7b. Ledger entries: ids zero-padded to three digits, the required
      field lines present, readout headings dated, and no entry past
      REVIEW-BY / KNOW-BY while still open.
  7c. `checked: DATE . source . stale after: N days` stamps whose window
      has blown.
  7d. BRIEFING.md whose `readout:` date (`updated:` when absent) is
      older than the newest ledger readout.
  8.  Clock vs the newest daily log: a log dated more than one day ahead
      of the clock FAILS (one day of grace for time zones).
  9.  Protected files that collapsed below 40% of their .bak copy
      (possible truncation). The checker DETECTS; the maintenance
      process is what writes the .bak files, and only after a clean run.

Reports, never fixes. Exit 0 with no FAIL, 1 with any FAIL, 2 on a usage
or config error (nothing on stdout), 3 on an internal error (traceback on
stderr). `--json` prints one object to stdout and nothing else:

    {"version": "0.2.0", "today": "YYYY-MM-DD",
     "fail": [...], "warn": [...], "info": [...]}

plus an "error" key after an internal error. Readers should ignore keys
they do not know; no key is removed or renamed inside a major version.

The clock is the machine's local calendar date, or the value of
`--today YYYY-MM-DD`, which exists to pin the clock for tests and to
reproduce an old report; the header line says when it was overridden.
A date is exactly YYYY-MM-DD and a real calendar day (one surrounding
pair of matching quotes is tolerated); anything else is a WARN naming the
file and the value, and that one comparison is skipped.

Configuration: an optional `icm-ops.json` at the workspace root (or the
file named by --config). Every key is optional; defaults are the ICM
conventions. Paths are relative to the workspace root, forward slashes;
an absolute path or a `..` segment is a config error (exit 2), as is an
unknown key. A leading UTF-8 BOM is tolerated.

    {
      "hot_budgets":        {"04-memory/STATE.md": 250, ...},   binding line budgets
      "protected":          ["CLAUDE.md", ...],                 truncation-guarded files
      "deliverable_markers":["/product/"],                      path substrings exempt
                                                                from orphan and frontmatter
                                                                rules; size WARNs only
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

Python 3 standard library only, 3.8 and newer. Every `.md` file (the
extension matched case-insensitively) is read once, as UTF-8: a leading
BOM is dropped, bytes that are not UTF-8 are replaced and reported once
(the file stays in every check), an unreadable file or an unlistable
directory is a WARN and the run continues. Symbolic links, junctions and
directory loops are not followed; a catalog row pointing inside one is
checked against the filesystem instead. stdout is switched to UTF-8
before anything is printed.
Formats: FORMAT.md in the icm-ops repository.
"""
import datetime
import json
import os
import pathlib
import posixpath
import re
import stat
import sys
import traceback
import urllib.parse

__version__ = "0.2.0"

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
LEDGER_FIELDS = {
    "L": ("CLAIM", "CONFIDENCE", "FALSIFIER", "COST", "REVIEW-BY", "OUTCOME"),
    "D": ("STAKES", "KNOW-BY", "RESOLVED"),
}
# CommonMark inline link: [text](<dest> "title") or [text](dest 'title').
LINK = re.compile(r"\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+(\"[^\"]*\"|'[^']*'))?\s*\)")
# CommonMark link reference definition, alone on its line: [label]: dest,
# optionally <dest>, optionally a quoted or parenthesised title. A footnote
# ([^1]: ...) is not one.
REF_DEF = re.compile(r"^[ \t]{0,3}\[(?!\^)[^\]]+\]:[ \t]*(<[^>]*>|\S+)"
                     r"(?:[ \t]+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?[ \t\r]*$", re.M)
USAGE = ("usage: python icm_check.py [workspace-root] [--json] [--config PATH] "
         "[--today YYYY-MM-DD] [--version]")


def die(msg, code=2):
    print(f"icm_check: {msg}", file=sys.stderr)
    if code == 2:
        print(USAGE, file=sys.stderr)
    sys.exit(code)


def parse_date(s):
    """The one date parser. Strips whitespace and one pair of matching
    quotes; wants exactly YYYY-MM-DD and a real calendar day. Returns a
    date or None. The regex decides the shape, so interpreters that also
    accept 20260908 or week dates give the same answer as older ones."""
    if s is None:
        return None
    s = str(s).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def parse_args(argv):
    root, as_json, config, today = None, False, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        elif a == "--version":
            print(f"icm_check {__version__}")
            sys.exit(0)
        elif a == "--json":
            as_json = True
        elif a in ("--config", "--today") or a.startswith(("--config=", "--today=")):
            if "=" in a:
                name, value = a.split("=", 1)
            else:
                name = a
                if i + 1 >= len(argv):
                    die(f"{a} needs a value")
                i += 1
                value = argv[i]
            if name == "--config":
                config = value
            else:
                today = parse_date(value)
                if today is None:
                    die(f"--today wants YYYY-MM-DD (a calendar date), got {value!r}")
        elif a.startswith("-"):
            die(f"unknown option: {a}")
        elif root is None:
            root = a
        else:
            die(f"unexpected argument: {a}")
        i += 1
    return root or ".", as_json, config, today


def norm(p):
    """Workspace-relative path in canonical form: forward slashes, no
    surrounding slashes, no './' or empty segments ('a//b', 'a/./b' and
    './a' all read as the same path). A '..' segment is the caller's to
    reject before calling: this collapses it."""
    p = str(p).replace("\\", "/").strip()
    p = posixpath.normpath(p).strip("/") if p.strip("/") else ""
    return "" if p == "." else p


def bad_path(v):
    """True for a path that is absolute or climbs with '..': config paths
    and catalog rows stay inside the workspace, so a typo cannot point a
    rule elsewhere."""
    s = str(v).replace("\\", "/").strip()
    return s.startswith("/") or re.match(r"[A-Za-z]:", s) is not None or ".." in s.split("/")


def plain_path(s):
    """Drop a Windows extended-length prefix (backslash backslash question
    backslash, with or without the UNC form) so the root resolves and
    prints like any other path."""
    if s.startswith("\\\\?\\UNC\\"):
        return "\\\\" + s[8:]
    if s.startswith("\\\\?\\"):
        return s[4:]
    return s


def load_config(root, explicit):
    cfg = json.loads(json.dumps(DEFAULTS))
    path = pathlib.Path(explicit) if explicit else root / "icm-ops.json"
    if explicit and not path.is_file():
        die(f"config not found: {path}")
    if path.exists() and not path.is_file():
        die(f"config {path} exists but is not a file")
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            die(f"cannot read config {path}: {e}")
        if not isinstance(data, dict):
            die(f"config {path} must be a JSON object")
        for k, v in data.items():
            if k not in DEFAULTS:
                die(f"unknown config key {k!r} in {path}; known: {', '.join(DEFAULTS)}")
            paths = ()  # values that must stay inside the workspace
            if k == "hot_budgets":
                if not isinstance(v, dict) or not all(
                        isinstance(kk, str) and isinstance(vv, int) and not isinstance(vv, bool) and vv > 0
                        for kk, vv in v.items()):
                    die("config hot_budgets must map path -> positive integer")
                if any(not norm(kk) for kk in v):
                    die("config hot_budgets keys must be non-empty paths")
                paths = tuple(v)
                v = {norm(kk): vv for kk, vv in v.items()}
            elif k in LIST_KEYS:
                if not isinstance(v, list) or not all(isinstance(x, str) and x for x in v):
                    die(f"config {k} must be a list of non-empty strings")
                if k in ("protected", "historical_dirs"):
                    paths = tuple(v)
                elif k == "deliverable_markers":
                    v = [m.replace("\\", "/") for m in v]  # substrings, matched against forward-slash paths
            elif k == "size_target_lines":
                if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                    die("config size_target_lines must be a positive integer")
            elif k in STR_KEYS:
                if not isinstance(v, str) or not v.strip():
                    die(f"config {k} must be a non-empty string")
                paths = (v,)
            for p in paths:
                if bad_path(p):
                    die(f"config {k} must hold relative paths inside the workspace "
                        f"(no absolute prefix, no '..' segment): {p!r}")
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


def load_text(path, rel, add):
    """Read one file as UTF-8. A leading BOM is dropped; bytes that are not
    UTF-8 are replaced and reported once; an unreadable file is reported
    and returns None so the caller drops it from every later check."""
    try:
        raw = path.read_bytes()
    except OSError as e:
        add("WARN", f"unreadable: {rel} ({e.strerror or e})")
        return None
    skipped = 0
    if raw.startswith(b"\xef\xbb\xbf"):
        raw, skipped = raw[3:], 3
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        add("WARN", f"not valid UTF-8: {rel} (byte 0x{raw[e.start]:02x} at offset {e.start + skipped})")
        return raw.decode("utf-8", errors="replace")


def is_link_or_loop(path, visited):
    """True for a symbolic link, a Windows reparse point (junction), or a
    directory whose real path the walk has already entered."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    attrs = getattr(st, "st_file_attributes", 0)  # Windows only
    if attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        return True
    return os.path.realpath(path) in visited


def md_files(root, add):
    """Walk the tree once. Returns (markdown files, seen, skipped): `seen`
    is every relative path the walk met, files and directories, exact
    case, so an existence question gets the same answer on every operating
    system; `skipped` is every link or loop the walk did not enter."""
    root_s = str(root)
    files, seen, skipped, visited = [], set(), set(), set()

    def onerror(e):
        where = getattr(e, "filename", None) or root_s
        add("WARN", f"could not list {norm(os.path.relpath(where, root_s))}: {e.strerror or e}")

    for dirpath, dirnames, filenames in os.walk(root_s, onerror=onerror):
        visited.add(os.path.realpath(dirpath))
        keep = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            seen.add(norm(os.path.relpath(full, root_s)))
            if d.startswith(".") or d in SKIP_DIRS:
                continue
            if is_link_or_loop(full, visited):
                skipped.add(norm(os.path.relpath(full, root_s)))
                add("WARN", f"skipped link or loop: {norm(os.path.relpath(full, root_s))}")
                continue
            keep.append(d)
        dirnames[:] = keep
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            seen.add(norm(os.path.relpath(full, root_s)))
            if fn.lower().endswith(".md"):
                files.append(pathlib.Path(full))
    return sorted(files), seen, skipped


def glob_files(root, rel_dir, pattern, add):
    """Files matching `pattern` directly under root/rel_dir; [] when the
    directory is absent, and a WARN instead of a crash when unlistable."""
    d = root / rel_dir
    if not d.is_dir():
        return []
    try:
        return sorted(p for p in d.glob(pattern) if p.is_file())
    except OSError as e:
        add("WARN", f"could not list {rel_dir}: {e.strerror or e}")
        return []


def frontmatter(text):
    """The block between an opening line that is exactly '---' (after an
    optional BOM, blank lines or blank space) and the next line that is
    exactly '---'; trailing whitespace on either fence is tolerated.
    Returns (block, terminated); (None, False) when there is no opening
    fence. An unterminated block returns everything after the opening
    fence with terminated=False; the caller decides what to do."""
    text = text.lstrip("\ufeff \t\r\n")
    lines = text.split("\n")
    if lines[0].rstrip() != "---":
        return None, False
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), True
    return "\n".join(lines[1:]), False


def fm_value(block, key):
    """Value of a top-level `key:` line in a frontmatter block, matched
    case-insensitively; None when absent."""
    m = re.search(r"^" + re.escape(key) + r"[ \t]*:[ \t]*(.*?)[ \t\r]*$", block, re.I | re.M)
    return m.group(1) if m else None


def strip_code(text):
    """Drop code before link scanning: fenced blocks (``` or ~~~; the
    closing fence uses the same character and is at least as long; an
    unclosed fence runs to the end of the file), inline code spans, and
    indented code (four spaces or a tab, opened after a blank line). Links
    inside code are examples, not links."""
    out, fence, blank, indented = [], None, True, False
    for line in text.split("\n"):
        if fence is None:
            m = re.match(r"[ \t]{0,3}(`{3,}|~{3,})", line)
            if m:
                fence = m.group(1)
                continue
            if line.startswith(("    ", "\t")) and (blank or indented):
                indented = True
            else:
                indented = False
                out.append(re.sub(r"(`+)[^\n]*?\1", "", line))
            blank = not line.strip()
        else:
            m = re.match(r"[ \t]{0,3}(`{3,}|~{3,})[ \t\r]*$", line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
    return "\n".join(out)


def run(root, cfg, today):
    findings = {"FAIL": [], "WARN": [], "INFO": []}

    def add(level, msg):
        findings[level].append(msg)

    markers = tuple(cfg["deliverable_markers"])
    hot = cfg["hot_budgets"]
    target = cfg["size_target_lines"]
    split_at = target * 2
    ledger_dir = root / cfg["ledger_dir"]
    frontmatter_exempt = set(cfg["frontmatter_exempt"])
    month_re = re.compile(re.escape(cfg["ledger_dir"]) + r"/2\d{3}-\d{2}\.md")

    def is_deliverable(rel):
        return any(m in "/" + rel + "/" for m in markers)

    def is_historical(rel):
        return (rel.startswith(tuple(cfg["historical_dirs"])) or is_deliverable(rel)
                or month_re.fullmatch(rel) is not None)

    # Walk once, read each file once. A file that cannot be read is
    # reported by load_text and dropped from every check below.
    files, seen, skipped = md_files(root, add)
    texts = {}
    for f in files:
        texts[f] = load_text(f, f.relative_to(root).as_posix(), add)
    files = [f for f in files if texts[f] is not None]
    rels = {f: f.relative_to(root).as_posix() for f in files}

    def text_of(f):
        """Cached read, for files reached by a glob rather than the walk."""
        if f not in texts:
            texts[f] = load_text(f, f.relative_to(root).as_posix(), add)
        return texts[f]

    def exists_rel(rel):
        """Existence against the walked tree (exact case on every OS). A
        path inside a directory the walk did not enter (dot-directories,
        node_modules, a skipped link or loop) is asked of the filesystem
        instead."""
        if rel in ("", "."):
            return True
        if rel in seen:
            return True
        top = rel.split("/", 1)[0]
        if top.startswith(".") or top in SKIP_DIRS or any(rel.startswith(s + "/") for s in skipped):
            return (root / rel).exists()
        return False

    catalog = root / cfg["catalog"]
    cat_text = text_of(catalog)
    if cat_text is None:
        add("FAIL", f"catalog could not be read: {cfg['catalog']}")
        cat_text = ""

    # --- 1. catalog rows -> existing paths ---------------------------------
    # A row's path cell may hold one path or several joined by " / "
    # (`CLAUDE.md` / `AGENTS.md`), each in backticks. Every backticked
    # token in that cell is a path; a path that is absolute or climbs out
    # of the workspace is reported and never covers anything.
    covered_prefixes = []
    for m in re.finditer(r"^\|([^|\n]*)\|", cat_text, re.M):
        for span in re.findall(r"`([^`]+)`", m.group(1)):
            for p in re.split(r"\s+/\s+", span.strip()):
                raw = p.strip().replace("\\", "/")
                if bad_path(raw):
                    add("WARN", f"catalog row path is absolute or has a .. segment: {p}")
                    continue
                rel = norm(raw)
                if not rel:
                    continue
                if not exists_rel(rel):
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
    # Inline links and reference definitions, with code stripped first.
    for f in files:
        rel = rels[f]
        base = rel.rsplit("/", 1)[0] if "/" in rel else ""
        prose = strip_code(texts[f])
        for href in [m.group(1) for m in LINK.finditer(prose)] + [m.group(1) for m in REF_DEF.finditer(prose)]:
            if href.startswith("<") and href.endswith(">"):
                href = href[1:-1]
            href = href.split("#", 1)[0]
            if not href:
                continue  # a bare fragment, or an empty destination
            if href.startswith("/") or re.match(r"[A-Za-z]:[\\/]", href):
                add("INFO", f"absolute link left unchecked in {rel}: ({href})")
                continue
            if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", href):
                continue  # a URL scheme: http, https, mailto, ...
            dest = urllib.parse.unquote(href).replace("\\", "/")
            joined = os.path.normpath(os.path.join(base, dest)).replace("\\", "/")
            if joined == "..":
                joined = "../"
            if joined.startswith("../"):
                ok = (root / joined).exists()  # leaves the workspace: ask the filesystem
            else:
                ok = exists_rel(joined)
            if not ok:
                add("FAIL", f"broken relative link in {rel}: ({href})")

    # --- 4. frontmatter present, terminated, `updated:` well-formed --------
    for f in files:
        rel = rels[f]
        if (f.name in frontmatter_exempt and "/" not in rel) or is_deliverable(rel):
            continue
        block, terminated = frontmatter(texts[f])
        if block is None:
            add("WARN", f"missing frontmatter: {rel}")
            continue
        if not terminated:
            add("WARN", f"unterminated frontmatter: {rel}")
        if f.name == "_TEMPLATE.md":
            continue  # templates carry the placeholder YYYY-MM-DD on purpose
        value = fm_value(block, "updated")
        if value is None:
            add("WARN", f"frontmatter without `updated:` in {rel}")
        elif parse_date(value) is None:
            add("WARN", f"malformed `updated:` in {rel}: {value!r} (want YYYY-MM-DD)")

    # --- 5. file sizes ------------------------------------------------------
    # Hot files carry BINDING budgets: over budget FAILS, because a WARN
    # that stays yellow for weeks becomes wallpaper. The fix is routine
    # compaction, not heroics.
    for f in files:
        rel = rels[f]
        n = count_lines(texts[f])
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
    # A budget that guards no file is a rule switched off, usually by a typo.
    walked = set(rels.values())
    for key in hot:
        if key not in walked:
            add("WARN", f"hot_budgets names no markdown file the walk found: {key}")

    # --- 6. catalog's own line rule ----------------------------------------
    # Soft and hard lines follow the catalog's hot budget when it has one
    # (155 -> warn past 150, fail past 170), else the 150/170 convention.
    # Over its hot budget, check 5 has already FAILed it: one defect, one FAIL.
    cat_lines = count_lines(cat_text)
    budget = hot.get(cfg["catalog"])
    soft, hard = (max(budget - 5, 1), budget + 15) if budget else (150, 170)
    if not (budget and cat_lines > budget and cfg["catalog"] in walked):
        lvl = "FAIL" if cat_lines > hard else ("WARN" if cat_lines > soft else "INFO")
        add(lvl, f"{catalog.name} is {cat_lines} lines (its own rule: keep under ~{soft})")

    # --- 7. decisions carry review-by; 7a. none is due ---------------------
    # Only the frontmatter counts: a date in the body is prose, not a clock.
    for f in glob_files(root, cfg["decisions_dir"], "[0-9]*.md", add):
        t = text_of(f)
        if t is None:
            continue
        block, _ = frontmatter(t)
        value = fm_value(block, "review-by") if block is not None else None
        if value is None:
            add("WARN", f"decision without review-by date: {f.name}")
            continue
        d = parse_date(value)
        if d is None:
            add("WARN", f"malformed date in {f.relative_to(root).as_posix()}: {value!r} "
                        "(want YYYY-MM-DD) at review-by:")
        elif d <= today:
            add("WARN", f"decision DUE FOR REVIEW: {f.name} (review-by {d.isoformat()}) — reopen or renew the date")

    # --- 7b. ledger clocks: readouts, entries past their date still open ---
    # The checker reads an entry's id, its dates, its open marker and
    # whether the required field lines exist. It never judges content.
    newest_readout, readouts = None, 0
    ledgers = glob_files(root, cfg["ledger_dir"], "2???-??.md", add)
    for f in glob_files(root, cfg["ledger_dir"], "*.md", add):
        if f not in ledgers and f.name not in ("BRIEFING.md", "README.md", "_TEMPLATE.md"):
            add("WARN", f"file in the ledger folder is not a YYYY-MM month file and is not read as a ledger: "
                        f"{cfg['ledger_dir']}/{f.name}")
    for f in ledgers:
        t = text_of(f)
        if t is None:
            continue
        rel = f.relative_to(root).as_posix()
        for m in re.finditer(r"^##\s*Readout\b([^\n]*)", t, re.I | re.M):
            dm = re.match(r"[^\n\d]{0,20}" + DATE, m.group(1))
            d = parse_date(dm.group(1)) if dm else None
            if d is None:
                add("WARN", f"readout heading without a parseable date in {f.name}: {m.group(0).strip()!r}")
                continue
            readouts += 1
            if newest_readout is None or d > newest_readout:
                newest_readout = d
        for block in re.split(r"(?m)^##[ \t]+", t):
            idm = re.match(r"([LD]-\d+)", block)
            if not idm:
                continue
            ident = idm.group(1)
            if len(ident) < 5:  # the letter, the dash, and at least three digits
                add("WARN", f"ledger id not zero-padded to three digits: {ident} ({f.name})")
            for field in LEDGER_FIELDS[ident[0]]:
                if not re.search(r"^" + field + r"[ \t]*:", block, re.I | re.M):
                    add("WARN", f"ledger {ident} lacks {field} line ({f.name})")
            due = re.search(r"^(REVIEW-BY|KNOW-BY)[ \t]*:[ \t]*(\S*)", block, re.I | re.M)
            is_open = re.search(r"^(?:OUTCOME|RESOLVED)[ \t]*:[ \t]*open\b", block, re.I | re.M)
            if not due:
                continue
            d = parse_date(due.group(2))
            if d is None:
                add("WARN", f"malformed date in {rel}: {due.group(2)!r} (want YYYY-MM-DD) "
                            f"at {ident} {due.group(1).upper()}")
            elif is_open and d < today:
                add("WARN", f"ledger {ident} past its date ({d.isoformat()}) and still open "
                            f"— resolve or mark EXPIRED ({f.name})")
    if ledger_dir.is_dir():
        if readouts:
            add("INFO", f"readouts found: {readouts} (newest {newest_readout.isoformat()})")
        else:
            add("INFO", "readouts found: 0")

    # --- 7c. checked-stamps: external numbers past their staleness window --
    # Convention: externally-sourced figures carry
    # "checked: YYYY-MM-DD · source · stale after: N days". A blown window
    # means the number describes the past while reading as the present.
    # A line break may sit inside the stamp; a blank line (LF or CRLF) may not.
    stamp = re.compile(r"checked:[ \t]*(\S+)(?:[^\r\n]|\r?\n(?!\r?\n)){0,120}?stale after:\s*(\d+)\s*day")
    for f in files:
        rel = rels[f]
        if is_historical(rel):
            continue
        for m in stamp.finditer(texts[f]):
            checked = parse_date(m.group(1))
            if checked is None:
                add("WARN", f"malformed date in {rel}: {m.group(1)!r} (want YYYY-MM-DD) at checked:")
                continue
            blown = (today - checked).days - int(m.group(2))
            if blown > 0:
                add("WARN", f"STALE ANCHOR in {rel}: checked {checked.isoformat()}, window {m.group(2)}d blown by "
                            f"{blown}d — re-check at the source or remove the number")

    # --- 7d. briefing staleness: a stale correction wears a fresh voice ----
    # BRIEFING.md carries `readout:` (the readout it was computed from);
    # `updated:` is the fallback, with a WARN, for files written before
    # format 1. A value that does not parse while a readout exists FAILS,
    # because staleness can then not be told at all.
    bf = ledger_dir / "BRIEFING.md"
    bt = text_of(bf) if bf.is_file() else None
    if bt is not None:
        block, _ = frontmatter(bt)
        block = block if block is not None else ""
        field, value = "readout", fm_value(block, "readout")
        if value is None:
            field, value = "updated", fm_value(block, "updated")
            if newest_readout:
                add("WARN", "BRIEFING.md has no readout: field — comparing updated: (format 1 wants readout:)")
        d = parse_date(value) if value is not None else None
        if newest_readout and d is None:
            add("FAIL", f"BRIEFING.md carries an unparseable readout:/updated: date ({(value or '')!r}) "
                        f"while a readout dated {newest_readout.isoformat()} exists")
        elif field == "readout" and value is not None and d is None:
            # check 4 already reports a malformed `updated:`; readout: is this check's own site
            add("WARN", f"malformed date in {cfg['ledger_dir']}/BRIEFING.md: {value!r} (want YYYY-MM-DD) at readout:")
        elif newest_readout and d < newest_readout:
            add("FAIL", f"BRIEFING.md ({field}: {d.isoformat()}) is OLDER than the newest ledger readout "
                        f"({newest_readout.isoformat()}) — regenerate it and the front-desk block")

    # --- 8. clock vs newest log (date tripwire) ----------------------------
    logs = glob_files(root, cfg["log_dir"], "2???-??-??.md", add)
    if logs:
        newest = logs[-1].stem
        d = parse_date(newest)
        if d is None:
            add("WARN", f"newest log has a non-date name: {newest}.md")
        else:
            age = (today - d).days
            when = f"{-age} day(s) ahead" if age < 0 else f"{age} day(s) old"
            add("INFO", f"clock says {today.isoformat()}; newest log is {newest} ({when})")
            if age < -1:
                add("FAIL", f"newest log {newest} is dated ahead of this machine's clock ({today.isoformat()}) "
                            "— a wrong clock on the writing or the reading side; --today pins the clock")

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
        try:
            if not f.is_file():
                continue
            if bak.is_file():
                cur, prev = f.stat().st_size, bak.stat().st_size
                if prev > 400 and cur < 0.4 * prev:
                    add("FAIL", f"POSSIBLE TRUNCATION: {rel} is {cur} bytes vs backup {prev} — recover from "
                                f"{rel}.bak; do NOT overwrite the .bak")
            else:
                add("INFO", f"no .bak yet for protected file {rel} — next maintenance run creates it")
        except OSError as e:
            add("WARN", f"unreadable: {rel} ({e.strerror or e})")

    return findings


def main(argv):
    root_arg, as_json, config_arg, today = parse_args(argv)
    root = pathlib.Path(plain_path(root_arg)).resolve()
    if not root.is_dir():
        die(f"workspace root is not a directory: {root_arg}")
    cfg, cfg_path = load_config(root, config_arg)
    if not (root / cfg["catalog"]).is_file():
        die(f"catalog not found: {root / cfg['catalog']} (not an ICM workspace, or set \"catalog\" in icm-ops.json)")
    overridden = today is not None
    if today is None:
        today = datetime.date.today()

    try:
        findings = run(root, cfg, today)
    except Exception as e:  # an internal error: report it, never a bare traceback and a lie of an exit code
        traceback.print_exc()
        what = f"{type(e).__name__}: {e}"
        if as_json:
            print(json.dumps({"version": __version__, "today": today.isoformat(),
                              "fail": [], "warn": [], "info": [],
                              "error": f"icm_check crashed: {what}"}, indent=2))
        else:
            print(f"icm_check: internal error — {what}", file=sys.stderr)
        return 3

    if as_json:
        print(json.dumps({"version": __version__, "today": today.isoformat(),
                          "fail": findings["FAIL"], "warn": findings["WARN"], "info": findings["INFO"]},
                         indent=2))
    else:
        where = f" (config: {cfg_path.name})" if cfg_path else " (defaults)"
        clock = today.isoformat() + (" (clock overridden by --today)" if overridden else "")
        print(f"icm_check {__version__} run {clock} on {root.name}{where} "
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
