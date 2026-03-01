#!/usr/bin/env python3
"""Inject EDGE hardening header into EDGE_*.html files.

Usage:
  python tools/harden_inject.py edge/EDGE_Foo_v1.html --exceptions clipboard
  python tools/harden_inject.py edge/EDGE_Bar_v1.html --exceptions download clipboard
  python tools/harden_inject.py edge/EDGE_Baz_v1.html   # no exceptions

Idempotent — skips files that already contain EDGE_HARDENING_V1.
"""

import argparse
import os
import re
import sys

# ── Snippet components ──────────────────────────────────────────

CSP_META = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; connect-src \'none\'; img-src \'self\' data:; style-src \'self\' \'unsafe-inline\'; script-src \'self\' \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'; frame-src \'none\'; object-src \'none\'"/>'

SHIM_TEMPLATE = """<!-- EDGE_HARDENING_V1 BEGIN -->
<script>
(function(){{
"use strict";
var EDGE_BUILD_ID="EDGE_BUILD_ID:{build_id}";
function _block(cap){{
  return function(){{throw new Error("EDGE hardening: "+cap+" is blocked")}};
}}
window.fetch          = _block("fetch");
window.XMLHttpRequest = _block("XMLHttpRequest");
window.WebSocket      = _block("WebSocket");
window.EventSource    = _block("EventSource");
try{{navigator.sendBeacon=_block("sendBeacon")}}catch(_){{}}
window.eval = _block("eval");
window.open = _block("window.open");
try{{Object.defineProperty(window,"localStorage",
  {{get:_block("localStorage"),configurable:false}})}}catch(_){{}}
try{{Object.defineProperty(window,"sessionStorage",
  {{get:_block("sessionStorage"),configurable:false}})}}catch(_){{}}
try{{Object.defineProperty(window,"indexedDB",
  {{get:_block("indexedDB"),configurable:false}})}}catch(_){{}}
document.addEventListener("DOMContentLoaded",function(){{
  var ext=document.querySelectorAll("script[src],link[href]");
  if(ext.length>0){{
    document.body.innerHTML=
      "<h1 style='color:red;font-family:monospace;padding:40px'>" +
      "EDGE VIOLATION: external resource detected (" +
      ext.length+" element(s))</h1>";
  }}
}});
}})();
</script>
<!-- EDGE_HARDENING_V1 END -->"""

ACTION_CONTRACT = """<!-- EDGE_ACTION_CONTRACT_V1 -->
<div id="edgeActionContract" style="
  margin:8px auto;max-width:1100px;width:94%;padding:6px 14px;
  border-radius:6px;border:1px solid rgba(57,255,20,.2);
  background:rgba(57,255,20,.04);
  font-family:'Courier New',Courier,monospace;font-size:.6rem;
  color:#8a80a0;display:flex;flex-wrap:wrap;gap:12px;align-items:center;
">
  <span style="color:#39ff14;font-weight:700;letter-spacing:1px">ACTION CONTRACT</span>
  <span>Network: LOCKED</span>
  <span style="opacity:.5">|</span>
  <span>Persistence: NONE</span>
  <span style="opacity:.5">|</span>
  <span>Side Effects: NONE</span>
</div>"""


def derive_build_id(filepath):
    """Derive a build ID from the filename."""
    base = os.path.basename(filepath)
    name = base.replace(".html", "")
    return name


def inject(filepath, exceptions):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Idempotency check
    if "EDGE_HARDENING_V1" in content:
        print("  SKIP  %s (already hardened)" % os.path.basename(filepath))
        return False

    build_id = derive_build_id(filepath)
    shim = SHIM_TEMPLATE.format(build_id=build_id)

    # Build exception tags
    exc_tags = []
    for exc in exceptions:
        exc_tags.append("<!-- EDGE_POLICY_EXCEPTION: %s -->" % exc)
    exc_block = "\n".join(exc_tags)

    # ── 1. Inject CSP + shim + exceptions after <head> ──
    head_match = re.search(r"<head[^>]*>", content, re.IGNORECASE)
    if not head_match:
        print("  FAIL  %s (no <head> tag found)" % os.path.basename(filepath))
        return False

    insert_pos = head_match.end()
    head_injection = "\n" + CSP_META + "\n" + shim + "\n"
    if exc_block:
        head_injection += exc_block + "\n"

    content = content[:insert_pos] + head_injection + content[insert_pos:]

    # ── 2. Inject Action Contract after <body> ──
    body_match = re.search(r"<body[^>]*>", content, re.IGNORECASE)
    if not body_match:
        print("  FAIL  %s (no <body> tag found)" % os.path.basename(filepath))
        return False

    # Find the first block-level element after <body> (header, div, h1, etc.)
    # Insert the action contract right after <body> open tag
    body_insert = body_match.end()
    content = content[:body_insert] + "\n" + ACTION_CONTRACT + "\n" + content[body_insert:]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    extras = ""
    if exceptions:
        extras = "  [exceptions: %s]" % ", ".join(exceptions)
    print("  DONE  %s%s" % (os.path.basename(filepath), extras))
    return True


def main():
    parser = argparse.ArgumentParser(description="Inject EDGE hardening header")
    parser.add_argument("files", nargs="+", help="EDGE HTML files to harden")
    parser.add_argument("--exceptions", nargs="*", default=[],
                        choices=["download", "clipboard"],
                        help="Policy exceptions to declare")
    args = parser.parse_args()

    count = 0
    for f in args.files:
        if inject(f, args.exceptions):
            count += 1

    print("\n  Hardened %d file(s)." % count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
