#!/usr/bin/env python3
"""Upgrade EDGE hardening shim in all EDGE_*.html files.

Replaces the EDGE_HARDENING_V1 BEGIN...END block with the latest shim,
preserving the EDGE_BUILD_ID value from the existing shim.

Usage:
  python tools/shim_upgrade.py edge/EDGE_Foo.html [edge/EDGE_Bar.html ...]
  python tools/shim_upgrade.py --all          # process all edge/EDGE_*.html
  python tools/shim_upgrade.py --all --root   # also process repo root EDGE_*.html

Idempotent — safe to run multiple times.
"""

import argparse
import glob
import os
import re
import sys

# ── The canonical v1.1 shim ─────────────────────────────────────
SHIM_V11 = """<!-- EDGE_HARDENING_V1 BEGIN -->
<script>
(function(){{
"use strict";
/* EDGE_HARDENING_V1 — Runtime capability lockdown v1.1 */

var EDGE_BUILD_ID="EDGE_BUILD_ID:{build_id}";

function _block(cap){{
  return function(){{throw new Error("EDGE hardening: "+cap+" is blocked")}};
}}

/* ── Network ──────────────────────────────────────────── */
window.fetch          = _block("fetch");
window.XMLHttpRequest = _block("XMLHttpRequest");
window.WebSocket      = _block("WebSocket");
window.EventSource    = _block("EventSource");
try{{navigator.sendBeacon=_block("sendBeacon")}}catch(_){{}}

/* ── Dynamic execution ────────────────────────────────── */
window.eval = _block("eval");
try{{window.Function=_block("Function constructor")}}catch(_){{}}

/* ── Navigation ───────────────────────────────────────── */
window.open = _block("window.open");

/* ── Communication channels ──────────────────────────── */
window.RTCPeerConnection       = _block("RTCPeerConnection");
window.webkitRTCPeerConnection = _block("RTCPeerConnection");
window.BroadcastChannel        = _block("BroadcastChannel");
window.SharedWorker            = _block("SharedWorker");
window.Worker                  = _block("Worker");

/* ── Persistence ──────────────────────────────────────── */
try{{Object.defineProperty(window,"localStorage",
  {{get:_block("localStorage"),configurable:false}})}}catch(_){{}}
try{{Object.defineProperty(window,"sessionStorage",
  {{get:_block("sessionStorage"),configurable:false}})}}catch(_){{}}
try{{Object.defineProperty(window,"indexedDB",
  {{get:_block("indexedDB"),configurable:false}})}}catch(_){{}}

/* ── Data channels ───────────────────────────────────── */
try{{Object.defineProperty(window,"name",
  {{value:"",writable:false,configurable:false}})}}catch(_){{}}

/* ── Build ID log ────────────────────────────────────── */
if(typeof console!=="undefined")console.log("[EDGE] Hardening active: "+EDGE_BUILD_ID);

/* ── Self-check: no external resources or injection ──── */
document.addEventListener("DOMContentLoaded",function(){{
  var violations=[];
  var ext=document.querySelectorAll("script[src],link[href]");
  if(ext.length>0)violations.push("external resource ("+ext.length+" element(s))");
  var handlers=document.querySelectorAll("[onclick],[onerror],[onload],[onmouseover],[onfocus],[onblur],[onsubmit],[onchange],[oninput]");
  if(handlers.length>0)violations.push("inline event handler ("+handlers.length+" element(s))");
  var bases=document.querySelectorAll("base[href]");
  if(bases.length>0)violations.push("base href hijack ("+bases.length+" element(s))");
  var refresh=document.querySelector("meta[http-equiv='refresh']");
  if(refresh)violations.push("meta refresh redirect");
  if(violations.length>0){{
    document.body.innerHTML=
      "<h1 style='color:red;font-family:monospace;padding:40px'>" +
      "EDGE VIOLATION: "+violations.join("; ")+"</h1>";
  }}
}});
}})();
</script>
<!-- EDGE_HARDENING_V1 END -->"""


def extract_build_id(content):
    """Extract the EDGE_BUILD_ID value from existing shim.

    The stored format is: EDGE_BUILD_ID="EDGE_BUILD_ID:MyModule_v1"
    We extract just the part after the colon prefix (e.g. "MyModule_v1").
    """
    m = re.search(r'EDGE_BUILD_ID="EDGE_BUILD_ID:([^"]+)"', content)
    if m:
        val = m.group(1).strip()
        if val and val != "SET_ME":
            return val
    return None


def upgrade_file(filepath):
    """Replace the shim block in one EDGE file. Returns (changed, detail)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "EDGE_HARDENING_V1 BEGIN" not in content:
        return False, "no shim found"

    # Already v1.1?
    if "capability lockdown v1.1" in content:
        return False, "already v1.1"

    # Extract build ID before replacement
    build_id = extract_build_id(content)
    if not build_id:
        # Derive from filename
        base = os.path.basename(filepath).replace(".html", "")
        build_id = base

    # Replace BEGIN...END block
    pattern = re.compile(
        r"<!-- EDGE_HARDENING_V1 BEGIN -->.*?<!-- EDGE_HARDENING_V1 END -->",
        re.DOTALL
    )
    new_shim = SHIM_V11.format(build_id=build_id)
    new_content, count = pattern.subn(new_shim, content)

    if count == 0:
        return False, "shim markers found but replacement failed"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True, "upgraded to v1.1 (build_id=%s)" % build_id


def main():
    parser = argparse.ArgumentParser(description="Upgrade EDGE hardening shim")
    parser.add_argument("files", nargs="*", help="EDGE HTML files to upgrade")
    parser.add_argument("--all", action="store_true",
                        help="Process all edge/EDGE_*.html files")
    parser.add_argument("--root", action="store_true",
                        help="Also process EDGE_*.html in repo root")
    args = parser.parse_args()

    files = list(args.files)
    if args.all:
        files.extend(sorted(glob.glob("edge/EDGE_*.html")))
    if args.root:
        files.extend(sorted(glob.glob("EDGE_*.html")))

    # Deduplicate
    seen = set()
    unique = []
    for f in files:
        norm = os.path.normpath(f)
        if norm not in seen:
            seen.add(norm)
            unique.append(f)
    files = unique

    if not files:
        print("No files specified. Use --all or list files.")
        return 1

    upgraded = 0
    for f in files:
        changed, detail = upgrade_file(f)
        fname = os.path.basename(f)
        status = "DONE" if changed else "SKIP"
        print("  %s  %s  (%s)" % (status, fname, detail))
        if changed:
            upgraded += 1

    print("\n  Upgraded %d / %d file(s)." % (upgraded, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
