#!/usr/bin/env python3
"""EDGE Hardening Linter — CI enforcement for Deep Sigma EDGE HTML modules.

Scans a directory for EDGE_*.html files and validates against the
Hardened EDGE security policy.  Non-EDGE HTML files are counted but
not inspected.

Exit codes:
  0 — all EDGE files pass
  1 — one or more violations detected
"""

import argparse
import glob
import os
import re
import sys

# ────────────────────────────────────────────────────────────────
# Forbidden patterns — checked on every line OUTSIDE the
# hardening-shim region (EDGE_HARDENING_V1 BEGIN / END).
# ────────────────────────────────────────────────────────────────

# Always forbidden (no exception relaxes these)
FORBIDDEN_ALWAYS = [
    # Network
    (r"\bfetch\s*\(",            "NETWORK: fetch()"),
    (r"\bXMLHttpRequest\b",      "NETWORK: XMLHttpRequest"),
    (r"\bWebSocket\b",           "NETWORK: WebSocket"),
    (r"\bEventSource\b",         "NETWORK: EventSource"),
    (r"\bsendBeacon\b",          "NETWORK: sendBeacon"),
    # Remote references
    (r"https?://",               "REMOTE_REF: http(s):// URL"),
    # External includes
    (r"<script\s[^>]*\bsrc\s*=", "EXTERNAL: <script src="),
    (r"<link\s[^>]*\bhref\s*=",  "EXTERNAL: <link href="),
    # Dynamic execution
    (r"\beval\s*\(",             "DYNAMIC_EXEC: eval()"),
    (r"\bnew\s+Function\s*\(",   "DYNAMIC_EXEC: new Function()"),
    (r"setTimeout\s*\(\s*[\"']", "DYNAMIC_EXEC: setTimeout(string)"),
    (r"setInterval\s*\(\s*[\"']","DYNAMIC_EXEC: setInterval(string)"),
    (r"\bimport\s*\(",           "DYNAMIC_EXEC: dynamic import()"),
    (r"\bimportScripts\s*\(",    "DYNAMIC_EXEC: importScripts()"),
    # Persistence
    (r"\blocalStorage\b",        "PERSISTENCE: localStorage"),
    (r"\bsessionStorage\b",      "PERSISTENCE: sessionStorage"),
    (r"\bindexedDB\b",           "PERSISTENCE: indexedDB"),
    (r"\bserviceWorker\b",       "PERSISTENCE: serviceWorker"),
]

# Forbidden unless "download" exception is declared
FORBIDDEN_DOWNLOAD = [
    (r"\bnew\s+Blob\b",          "DOWNLOAD: Blob constructor (needs <!-- EDGE_POLICY_EXCEPTION: download -->)"),
    (r"\bcreateObjectURL\b",     "DOWNLOAD: createObjectURL (needs <!-- EDGE_POLICY_EXCEPTION: download -->)"),
    (r"\brevokeObjectURL\b",     "DOWNLOAD: revokeObjectURL (needs <!-- EDGE_POLICY_EXCEPTION: download -->)"),
]

# Forbidden unless "clipboard" exception is declared
FORBIDDEN_CLIPBOARD = [
    (r"navigator\.clipboard\b",  "CLIPBOARD: navigator.clipboard (needs <!-- EDGE_POLICY_EXCEPTION: clipboard -->)"),
]

# Always forbidden even WITH clipboard exception
CLIPBOARD_NEVER = [
    (r"\.readText\s*\(",         "CLIPBOARD: readText() is NEVER allowed"),
]

# ────────────────────────────────────────────────────────────────
# Required markers (must appear SOMEWHERE in the file)
# ────────────────────────────────────────────────────────────────

REQUIRED_MARKERS = [
    ("connect-src 'none'",       "CSP meta: connect-src 'none'"),
    ("EDGE_ACTION_CONTRACT_V1",  "Action Contract marker: EDGE_ACTION_CONTRACT_V1"),
    ("Network: LOCKED",          "Action Contract: Network: LOCKED"),
    ("Persistence: NONE",        "Action Contract: Persistence: NONE"),
    ("Side Effects: NONE",       "Action Contract: Side Effects: NONE"),
    ("EDGE_HARDENING_V1",        "Hardening shim marker: EDGE_HARDENING_V1"),
    ("EDGE_BUILD_ID",            "Build ID marker: EDGE_BUILD_ID"),
]

ALLOWED_EXCEPTIONS = {"download", "clipboard"}
SHIM_BEGIN = "EDGE_HARDENING_V1 BEGIN"
SHIM_END = "EDGE_HARDENING_V1 END"


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def parse_exceptions(content):
    """Return list of declared EDGE_POLICY_EXCEPTION values."""
    return re.findall(r"<!--\s*EDGE_POLICY_EXCEPTION:\s*(\S+)\s*-->", content)


def lint_file(filepath):
    """Lint one EDGE file. Returns (violations_list, exceptions_list)."""
    with open(filepath, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    content = "".join(lines)
    violations = []

    # ── 1. Parse & validate exception tags ──────────────────
    exceptions = parse_exceptions(content)
    exception_set = set(exceptions)
    for exc in exceptions:
        if exc not in ALLOWED_EXCEPTIONS:
            violations.append(
                (0, 'INVALID_EXCEPTION: "%s" — allowed: %s'
                 % (exc, ", ".join(sorted(ALLOWED_EXCEPTIONS))))
            )

    # ── 2. Required markers ─────────────────────────────────
    for marker, label in REQUIRED_MARKERS:
        if marker not in content:
            violations.append((0, "MISSING: %s" % label))

    # ── 3. Identify hardening-shim region (skip zone) ───────
    shim_ranges = []
    shim_start = None
    for idx, line in enumerate(lines):
        if SHIM_BEGIN in line:
            shim_start = idx
        elif SHIM_END in line and shim_start is not None:
            shim_ranges.append((shim_start, idx))
            shim_start = None

    def in_shim(lineno):
        for s, e in shim_ranges:
            if s <= lineno <= e:
                return True
        return False

    # ── 4. Build active forbidden list ──────────────────────
    active = list(FORBIDDEN_ALWAYS)
    if "download" not in exception_set:
        active.extend(FORBIDDEN_DOWNLOAD)
    if "clipboard" not in exception_set:
        active.extend(FORBIDDEN_CLIPBOARD)
    active.extend(CLIPBOARD_NEVER)  # always checked

    # ── 5. Line-by-line scan ────────────────────────────────
    for idx, line in enumerate(lines):
        if in_shim(idx):
            continue
        if "EDGE_POLICY_EXCEPTION:" in line:
            continue
        for pattern, label in active:
            flags = re.IGNORECASE if label.startswith("REMOTE_REF") else 0
            if re.search(pattern, line, flags):
                violations.append((idx + 1, label))

    return violations, exceptions


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EDGE Hardening Linter — CI enforcement for EDGE HTML modules"
    )
    parser.add_argument(
        "--path", default=None,
        help="Directory to scan (default: $GITHUB_WORKSPACE or cwd)"
    )
    args = parser.parse_args()
    root = args.path or os.environ.get("GITHUB_WORKSPACE", ".")

    # Discover files
    all_html = sorted(glob.glob(os.path.join(root, "*.html")))
    edge_files = [f for f in all_html if os.path.basename(f).startswith("EDGE_")]

    total_html = len(all_html)
    total_edge = len(edge_files)
    total_failures = 0
    total_exceptions = 0
    failed_files = []

    print("[EDGE Lint] directory: %s" % os.path.abspath(root))
    print()

    if total_edge == 0:
        print("  (no EDGE_*.html files found)")
        print()
        _summary(total_html, 0, 0, 0)
        print("[EDGE Lint] PASS (nothing to check)")
        return 0

    print("[EDGE Lint] Scanning %d EDGE file(s)...\n" % total_edge)

    for filepath in edge_files:
        fname = os.path.basename(filepath)
        violations, exceptions = lint_file(filepath)
        total_exceptions += len(exceptions)

        if violations:
            total_failures += len(violations)
            failed_files.append(fname)
            print("  FAIL  %s" % fname)
            for lineno, msg in violations:
                loc = "L%d" % lineno if lineno > 0 else "file"
                print("        [%s] %s" % (loc, msg))
            if exceptions:
                print("        exceptions declared: %s" % ", ".join(exceptions))
            print()
        else:
            extras = ""
            if exceptions:
                extras = "  [exceptions: %s]" % ", ".join(exceptions)
            print("  PASS  %s%s" % (fname, extras))

    print()
    _summary(total_html, total_edge, total_failures, total_exceptions)

    if total_failures > 0:
        print("[EDGE Lint] FAIL — %d file(s) with violations" % len(failed_files))
        return 1
    else:
        print("[EDGE Lint] PASS — all EDGE files comply")
        return 0


def _summary(html, edge, fail, exc):
    bar = "\u2500" * 52
    print(bar)
    print("  total_html_found:    %d" % html)
    print("  edge_files_scanned:  %d" % edge)
    print("  failures:            %d" % fail)
    print("  exceptions_used:     %d" % exc)
    print(bar)


if __name__ == "__main__":
    sys.exit(main())
