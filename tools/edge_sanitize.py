#!/usr/bin/env python3
"""EDGE Sanitizer — Remove forbidden APIs (localStorage, sessionStorage, fetch, URLs)
from EDGE_*.html files, converting persistence to in-memory equivalents.

Usage:
  python tools/edge_sanitize.py edge/EDGE_Foo.html [edge/EDGE_Bar.html ...]
  python tools/edge_sanitize.py --all          # process all edge/EDGE_*.html

Reports changes per file. Idempotent — safe to run multiple times.
"""

import argparse
import glob
import os
import re
import sys


def sanitize_file(filepath):
    """Remove forbidden API usage from one EDGE file. Returns (changes_count, details)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    changes = []

    # ── Identify hardening shim region (skip it) ──
    shim_begin = content.find("EDGE_HARDENING_V1 BEGIN")
    shim_end = content.find("EDGE_HARDENING_V1 END")

    def outside_shim(match_start):
        if shim_begin < 0 or shim_end < 0:
            return True
        return match_start < shim_begin or match_start > shim_end

    # ═══════════════════════════════════════════════════════
    # Pattern A: storageAvailable() / storageOk() functions
    # Replace entire helper blocks with memory-only versions
    # ═══════════════════════════════════════════════════════

    # Pattern: storageAvailable() { try { localStorage.setItem... } }
    # Found in BOE, BidNoBid, ComplianceMatrix, Hiring
    pat_sa = re.compile(
        r'function\s+storageAvailable\s*\(\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    for m in pat_sa.finditer(content):
        if outside_shim(m.start()):
            changes.append("removed storageAvailable()")

    content = pat_sa.sub(
        'function storageAvailable(){return false}',
        content
    )

    # Pattern: storageOk() — JRM files
    pat_sok = re.compile(
        r'function\s+storageOk\s*\(\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    for m in pat_sok.finditer(content):
        if outside_shim(m.start()):
            changes.append("removed storageOk()")

    content = pat_sok.sub(
        'function storageOk(){return false}',
        content
    )

    # ═══════════════════════════════════════════════════════
    # Pattern B: getStoreItem/setStoreItem/removeStoreItem
    # Replace with memory-only versions
    # ═══════════════════════════════════════════════════════

    # getStoreItem
    pat_gsi = re.compile(
        r'function\s+getStoreItem\s*\(\s*k\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    if pat_gsi.search(content):
        content = pat_gsi.sub(
            'function getStoreItem(k){'
            'window.__ds_memstore=window.__ds_memstore||{};'
            'return window.__ds_memstore[k]||null'
            '}',
            content
        )
        changes.append("replaced getStoreItem() with memory-only")

    # setStoreItem
    pat_ssi = re.compile(
        r'function\s+setStoreItem\s*\(\s*k\s*,\s*v\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    if pat_ssi.search(content):
        content = pat_ssi.sub(
            'function setStoreItem(k,v){'
            'window.__ds_memstore=window.__ds_memstore||{};'
            'window.__ds_memstore[k]=v'
            '}',
            content
        )
        changes.append("replaced setStoreItem() with memory-only")

    # removeStoreItem
    pat_rsi = re.compile(
        r'function\s+removeStoreItem\s*\(\s*k\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    if pat_rsi.search(content):
        content = pat_rsi.sub(
            'function removeStoreItem(k){'
            'window.__ds_memstore=window.__ds_memstore||{};'
            'delete window.__ds_memstore[k]'
            '}',
            content
        )
        changes.append("replaced removeStoreItem() with memory-only")

    # ═══════════════════════════════════════════════════════
    # Pattern C: getStore/setStore (JRM pattern)
    # ═══════════════════════════════════════════════════════

    pat_gs = re.compile(
        r'function\s+getStore\s*\(\s*k\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    if pat_gs.search(content):
        content = pat_gs.sub(
            'function getStore(k){'
            'window.__mem=window.__mem||{};'
            'return window.__mem[k]||null'
            '}',
            content
        )
        changes.append("replaced getStore() with memory-only")

    pat_ss = re.compile(
        r'function\s+setStore\s*\(\s*k\s*,\s*v\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    if pat_ss.search(content):
        content = pat_ss.sub(
            'function setStore(k,v){'
            'window.__mem=window.__mem||{};'
            'window.__mem[k]=v'
            '}',
            content
        )
        changes.append("replaced setStore() with memory-only")

    # ═══════════════════════════════════════════════════════
    # Pattern D: readJson/writeJson (Suite ReadOnly)
    # ═══════════════════════════════════════════════════════

    pat_rj = re.compile(
        r'function\s+readJson\s*\(\s*key\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    if pat_rj.search(content):
        content = pat_rj.sub(
            'function readJson(key){'
            'window.__ds_memstore=window.__ds_memstore||{};'
            'var raw=window.__ds_memstore[key];'
            'if(!raw)return null;'
            'try{return JSON.parse(raw)}catch(_){return null}'
            '}',
            content
        )
        changes.append("replaced readJson() with memory-only")

    pat_wj = re.compile(
        r'function\s+writeJson\s*\(\s*key\s*,\s*val\s*\)\s*\{[^}]*localStorage[^}]*\}',
        re.DOTALL
    )
    if pat_wj.search(content):
        content = pat_wj.sub(
            'function writeJson(key,val){'
            'window.__ds_memstore=window.__ds_memstore||{};'
            'window.__ds_memstore[key]=JSON.stringify(val)'
            '}',
            content
        )
        changes.append("replaced writeJson() with memory-only")

    # ═══════════════════════════════════════════════════════
    # Pattern E: ABP telemetry — remove try{localStorage.setItem("ds_abp_v1"...)}
    # ═══════════════════════════════════════════════════════

    pat_abp = re.compile(
        r'try\s*\{\s*localStorage\.setItem\s*\(\s*["\']ds_abp_v1["\']\s*,'
        r'[^}]*\}\s*catch\s*\(\s*_?\s*\)\s*\{[^}]*\}',
        re.DOTALL
    )
    for m in pat_abp.finditer(content):
        if outside_shim(m.start()):
            changes.append("removed ABP telemetry localStorage call")
    content = pat_abp.sub('/* ABP persistence removed (EDGE hardened) */', content)

    # Simpler ABP pattern without try/catch
    pat_abp2 = re.compile(
        r'localStorage\.setItem\s*\(\s*["\']ds_abp_v1["\']',
    )
    # Only replace outside shim
    lines = content.split('\n')
    new_lines = []
    shim_active = False
    for line in lines:
        if 'EDGE_HARDENING_V1 BEGIN' in line:
            shim_active = True
        elif 'EDGE_HARDENING_V1 END' in line:
            shim_active = False

        if not shim_active and pat_abp2.search(line):
            new_lines.append(line.replace(
                pat_abp2.search(line).group(),
                '/* ABP persistence removed */'
            ))
            changes.append("removed ABP localStorage.setItem")
        else:
            new_lines.append(line)
    content = '\n'.join(new_lines)

    # ═══════════════════════════════════════════════════════
    # Pattern F: Remaining direct localStorage/sessionStorage calls
    # outside shim and outside exception/policy lines
    # ═══════════════════════════════════════════════════════

    # Direct localStorage.getItem/setItem/removeItem remaining
    remaining_ls = re.compile(r'\blocalStorage\b')
    remaining_ss = re.compile(r'\bsessionStorage\b')

    lines = content.split('\n')
    new_lines = []
    shim_active = False
    for i, line in enumerate(lines):
        if 'EDGE_HARDENING_V1 BEGIN' in line:
            shim_active = True
        elif 'EDGE_HARDENING_V1 END' in line:
            shim_active = False

        if shim_active or 'EDGE_POLICY_EXCEPTION' in line:
            new_lines.append(line)
            continue

        modified = line

        # localStorage.getItem(key)
        modified = re.sub(
            r'localStorage\.getItem\s*\(\s*([^)]+)\s*\)',
            r'((window.__ds_memstore||{})[\1]||null)',
            modified
        )

        # localStorage.setItem(key, val)
        modified = re.sub(
            r'localStorage\.setItem\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'(window.__ds_memstore=window.__ds_memstore||{},window.__ds_memstore[\1]=\2)',
            modified
        )

        # localStorage.removeItem(key)
        modified = re.sub(
            r'localStorage\.removeItem\s*\(\s*([^)]+)\s*\)',
            r'(window.__ds_memstore=window.__ds_memstore||{},delete window.__ds_memstore[\1])',
            modified
        )

        # sessionStorage.getItem(key)
        modified = re.sub(
            r'sessionStorage\.getItem\s*\(\s*([^)]+)\s*\)',
            r'((window.__ds_sessmem||{})[\1]||null)',
            modified
        )

        # sessionStorage.setItem(key, val)
        modified = re.sub(
            r'sessionStorage\.setItem\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'(window.__ds_sessmem=window.__ds_sessmem||{},window.__ds_sessmem[\1]=\2)',
            modified
        )

        # sessionStorage.removeItem(key)
        modified = re.sub(
            r'sessionStorage\.removeItem\s*\(\s*([^)]+)\s*\)',
            r'(window.__ds_sessmem=window.__ds_sessmem||{},delete window.__ds_sessmem[\1])',
            modified
        )

        # Remaining bare localStorage / sessionStorage references (in comments etc.)
        if remaining_ls.search(modified) or remaining_ss.search(modified):
            # Check if it's in a comment
            stripped = modified.lstrip()
            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                modified = modified.replace('localStorage', 'mem-store')
                modified = modified.replace('sessionStorage', 'sess-mem')
            elif '<!--' in modified:
                modified = modified.replace('localStorage', 'mem-store')
                modified = modified.replace('sessionStorage', 'sess-mem')

        if modified != line:
            changes.append("L%d: replaced storage call" % (i + 1))

        new_lines.append(modified)

    content = '\n'.join(new_lines)

    # ═══════════════════════════════════════════════════════
    # Pattern G: URL placeholders in form fields / textareas
    # Encode :// as %3A%2F%2F in placeholder URLs
    # ═══════════════════════════════════════════════════════

    # Match http(s):// that are inside placeholder, value, or textarea content
    # but NOT inside data: URIs (already handled) or the shim
    lines = content.split('\n')
    new_lines = []
    shim_active = False
    for i, line in enumerate(lines):
        if 'EDGE_HARDENING_V1 BEGIN' in line:
            shim_active = True
        elif 'EDGE_HARDENING_V1 END' in line:
            shim_active = False

        if shim_active or 'EDGE_POLICY_EXCEPTION' in line:
            new_lines.append(line)
            continue

        modified = line

        # Replace http:// and https:// outside shim
        # But preserve data: URIs (already percent-encoded above)
        if re.search(r'https?://', modified, re.IGNORECASE):
            # Check if it's inside a data: URI — if so, encode the namespace
            if 'data:' in modified:
                modified = re.sub(
                    r"xmlns='http://www\.w3\.org/2000/svg'",
                    "xmlns='http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg'",
                    modified
                )
                modified = re.sub(
                    r'xmlns="http://www\.w3\.org/2000/svg"',
                    'xmlns="http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg"',
                    modified
                )
            # For placeholder URLs in HTML attributes
            modified = re.sub(
                r'(placeholder=["\'][^"\']*?)https?://',
                lambda m: m.group(1) + 'https%3A%2F%2F',
                modified,
                flags=re.IGNORECASE
            )
            # For value attributes with URLs
            modified = re.sub(
                r'(value=["\'][^"\']*?)https?://',
                lambda m: m.group(1) + 'https%3A%2F%2F',
                modified,
                flags=re.IGNORECASE
            )

        if modified != line:
            changes.append("L%d: encoded URL placeholder" % (i + 1))

        new_lines.append(modified)

    content = '\n'.join(new_lines)

    # ═══════════════════════════════════════════════════════
    # Write back if changed
    # ═══════════════════════════════════════════════════════

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return len(changes), changes


def main():
    parser = argparse.ArgumentParser(description="EDGE Sanitizer")
    parser.add_argument("files", nargs="*", help="EDGE HTML files to sanitize")
    parser.add_argument("--all", action="store_true",
                        help="Process all edge/EDGE_*.html files")
    args = parser.parse_args()

    if args.all:
        files = sorted(glob.glob("edge/EDGE_*.html"))
    else:
        files = args.files

    if not files:
        print("No files specified. Use --all or list files.")
        return 1

    total_changes = 0
    for f in files:
        count, details = sanitize_file(f)
        fname = os.path.basename(f)
        if count > 0:
            print("  %3d changes  %s" % (count, fname))
            for d in details[:5]:
                print("              %s" % d)
            if len(details) > 5:
                print("              ... and %d more" % (len(details) - 5))
        else:
            print("    0 changes  %s (already clean)" % fname)
        total_changes += count

    print("\n  Total: %d changes across %d files." % (total_changes, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
