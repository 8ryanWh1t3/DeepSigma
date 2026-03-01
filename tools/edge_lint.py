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
import json
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
    (r"setTimeout\s*\(\s*(?:/\*.*?\*/\s*)*[\"']", "DYNAMIC_EXEC: setTimeout(string)"),
    (r"setInterval\s*\(\s*(?:/\*.*?\*/\s*)*[\"']", "DYNAMIC_EXEC: setInterval(string)"),
    (r"\bimport\s*\(",           "DYNAMIC_EXEC: dynamic import()"),
    (r"\bimportScripts\s*\(",    "DYNAMIC_EXEC: importScripts()"),
    # Persistence
    (r"\blocalStorage\b",        "PERSISTENCE: localStorage"),
    (r"\bsessionStorage\b",      "PERSISTENCE: sessionStorage"),
    (r"\bindexedDB\b",           "PERSISTENCE: indexedDB"),
    (r"\bserviceWorker\b",       "PERSISTENCE: serviceWorker"),
    # Note: inline event handlers (onclick=, etc.) are acceptable in
    # self-contained EDGE files where all content is author-controlled.
    # The CSP blocks injection of new handlers from external sources.
    # HTML injection vectors
    (r"<form\s[^>]*\baction\s*=", "FORM_ACTION: <form action="),
    (r"<meta\s[^>]*http-equiv\s*=\s*[\"']?\s*refresh",
                                  "META_REFRESH: meta http-equiv=refresh"),
    (r"<base\s[^>]*\bhref\s*=",  "BASE_HIJACK: <base href="),
    # Communication channels
    (r"\bRTCPeerConnection\b",   "WEBRTC: RTCPeerConnection"),
    (r"\bRTCDataChannel\b",      "WEBRTC: RTCDataChannel"),
    (r"\bmediaDevices\b",        "WEBRTC: mediaDevices"),
    (r"\bBroadcastChannel\b",    "COMMS: BroadcastChannel"),
    (r"\bSharedWorker\b",        "COMMS: SharedWorker"),
    (r"\.postMessage\s*\(",      "COMMS: postMessage()"),
    (r"\bwindow\.name\s*=",      "EXFIL: window.name assignment"),
    # Worker constructor
    (r"\bnew\s+Worker\s*\(",     "WORKER: Worker constructor"),
    # Module/import map injection
    (r"<script\s[^>]*type\s*=\s*[\"']importmap",
                                  "IMPORT_MAP: <script type=importmap"),
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
# Full-content patterns — checked against the ENTIRE file content
# (outside shim) to catch multiline evasion.
# ────────────────────────────────────────────────────────────────

MULTILINE_PATTERNS = [
    (r"\bfetch\s*\(",            "NETWORK: fetch() [multiline]"),
    (r"\beval\s*\(",             "DYNAMIC_EXEC: eval() [multiline]"),
    (r"\bnew\s+Function\s*\(",   "DYNAMIC_EXEC: new Function() [multiline]"),
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


def lint_file(filepath, strict=False):
    """Lint one EDGE file. Returns (violations_list, warnings_list, exceptions_list)."""
    with open(filepath, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    content = "".join(lines)
    violations = []
    warnings = []

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

    # ── 3. Build ID validation ──────────────────────────────
    if "EDGE_BUILD_ID:SET_ME" in content:
        msg = "BUILD_ID: still set to SET_ME — update to module name"
        if strict:
            violations.append((0, msg))
        else:
            warnings.append((0, msg))

    # ── 4. Identify hardening-shim region (skip zone) ───────
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

    # ── 5. Build active forbidden list ──────────────────────
    active = list(FORBIDDEN_ALWAYS)
    if "download" not in exception_set:
        active.extend(FORBIDDEN_DOWNLOAD)
    if "clipboard" not in exception_set:
        active.extend(FORBIDDEN_CLIPBOARD)
    active.extend(CLIPBOARD_NEVER)  # always checked

    # ── 6. Line-by-line scan ────────────────────────────────
    for idx, line in enumerate(lines):
        if in_shim(idx):
            continue
        if "EDGE_POLICY_EXCEPTION:" in line:
            continue
        for pattern, label in active:
            flags = re.IGNORECASE if label.startswith("REMOTE_REF") else 0
            if re.search(pattern, line, flags):
                violations.append((idx + 1, label))

    # ── 7. Multiline scan (full content outside shim) ───────
    # Build content excluding shim regions
    non_shim_lines = []
    for idx, line in enumerate(lines):
        if in_shim(idx):
            non_shim_lines.append("")  # preserve line numbering
        elif "EDGE_POLICY_EXCEPTION:" in line:
            non_shim_lines.append("")
        else:
            non_shim_lines.append(line)
    non_shim_content = "".join(non_shim_lines)

    for pattern, label in MULTILINE_PATTERNS:
        for m in re.finditer(pattern, non_shim_content, re.DOTALL):
            # Find line number from match position
            lineno = non_shim_content[:m.start()].count("\n") + 1
            # Only add if not already caught by line-by-line scan
            already = any(v[1] == label.replace(" [multiline]", "") and v[0] == lineno
                          for v in violations)
            if not already:
                violations.append((lineno, label))

    return violations, warnings, exceptions


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

DEFAULT_SCAN_DIRS = ["edge", "enterprise/edge", "core/edge"]


def _discover_edge_files(root):
    """Discover EDGE_*.html files in a single directory."""
    all_html = sorted(glob.glob(os.path.join(root, "*.html")))
    edge_files = [f for f in all_html if os.path.basename(f).startswith("EDGE_")]
    return all_html, edge_files


def main():
    parser = argparse.ArgumentParser(
        description="EDGE Hardening Linter — CI enforcement for EDGE HTML modules"
    )
    parser.add_argument(
        "--path", default=None,
        help="Directory to scan (default: scans edge/, enterprise/edge/, core/edge/)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Treat warnings (e.g. BUILD_ID=SET_ME) as errors"
    )
    args = parser.parse_args()

    # Determine directories to scan
    if args.path:
        scan_dirs = [args.path]
    else:
        workspace = os.environ.get("GITHUB_WORKSPACE", ".")
        scan_dirs = [os.path.join(workspace, d) for d in DEFAULT_SCAN_DIRS]

    total_html = 0
    total_edge = 0
    total_failures = 0
    total_warnings = 0
    total_exceptions = 0
    failed_files = []
    json_results = []
    all_edge_files = []

    # Collect files from all directories
    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        dir_html, dir_edge = _discover_edge_files(scan_dir)
        total_html += len(dir_html)
        total_edge += len(dir_edge)
        all_edge_files.extend(dir_edge)

    if not args.json_output:
        dirs_str = ", ".join(os.path.abspath(d) for d in scan_dirs if os.path.isdir(d))
        print("[EDGE Lint] directories: %s" % dirs_str)
        print()

    if total_edge == 0:
        if args.json_output:
            print(json.dumps({
                "directories": [os.path.abspath(d) for d in scan_dirs if os.path.isdir(d)],
                "total_html": total_html,
                "edge_files": 0,
                "failures": 0,
                "warnings": 0,
                "exceptions": 0,
                "result": "PASS",
                "files": []
            }, indent=2))
        else:
            print("  (no EDGE_*.html files found)")
            print()
            _summary(total_html, 0, 0, 0, 0)
            print("[EDGE Lint] PASS (nothing to check)")
        return 0

    if not args.json_output:
        print("[EDGE Lint] Scanning %d EDGE file(s)...\n" % total_edge)

    for filepath in all_edge_files:
        # Show relative path for multi-dir scanning
        fname = os.path.relpath(filepath)
        violations, warnings, exceptions = lint_file(filepath, strict=args.strict)
        total_exceptions += len(exceptions)
        total_warnings += len(warnings)

        file_result = {
            "file": fname,
            "violations": [{"line": v[0], "message": v[1]} for v in violations],
            "warnings": [{"line": w[0], "message": w[1]} for w in warnings],
            "exceptions": exceptions,
            "result": "FAIL" if violations else "PASS"
        }
        json_results.append(file_result)

        if violations:
            total_failures += len(violations)
            failed_files.append(fname)
            if not args.json_output:
                print("  FAIL  %s" % fname)
                for lineno, msg in violations:
                    loc = "L%d" % lineno if lineno > 0 else "file"
                    print("        [%s] %s" % (loc, msg))
                if warnings:
                    for _, msg in warnings:
                        print("        [warn] %s" % msg)
                if exceptions:
                    print("        exceptions declared: %s" % ", ".join(exceptions))
                print()
        else:
            if not args.json_output:
                extras = ""
                if exceptions:
                    extras = "  [exceptions: %s]" % ", ".join(exceptions)
                warn_str = ""
                if warnings:
                    warn_str = "  [%d warning(s)]" % len(warnings)
                print("  PASS  %s%s%s" % (fname, extras, warn_str))

    if args.json_output:
        print(json.dumps({
            "directories": [os.path.abspath(d) for d in scan_dirs if os.path.isdir(d)],
            "total_html": total_html,
            "edge_files": total_edge,
            "failures": total_failures,
            "warnings": total_warnings,
            "exceptions": total_exceptions,
            "result": "FAIL" if total_failures > 0 else "PASS",
            "files": json_results
        }, indent=2))
    else:
        print()
        _summary(total_html, total_edge, total_failures, total_exceptions, total_warnings)

        if total_failures > 0:
            print("[EDGE Lint] FAIL — %d file(s) with violations" % len(failed_files))
        else:
            print("[EDGE Lint] PASS — all EDGE files comply")

    return 1 if total_failures > 0 else 0


def _summary(html, edge, fail, exc, warn=0):
    bar = "\u2500" * 52
    print(bar)
    print("  total_html_found:    %d" % html)
    print("  edge_files_scanned:  %d" % edge)
    print("  failures:            %d" % fail)
    print("  warnings:            %d" % warn)
    print("  exceptions_used:     %d" % exc)
    print(bar)


if __name__ == "__main__":
    sys.exit(main())
