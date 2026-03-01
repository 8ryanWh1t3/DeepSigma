# EDGE Hardening Policy

Every `EDGE_*.html` module in this repository is a **self-contained, offline-only, zero-dependency** tool. This document describes the security policy enforced by CI and how to comply with it.

---

## What is enforced

The CI linter (`tools/edge_lint.py`) runs on every push to `main` and every pull request. It scans all `EDGE_*.html` files in the repo root and **fails the build** if any file violates the policy.

### A. Forbidden capabilities

| Category | Blocked patterns |
|---|---|
| **Network** | `fetch()`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon` |
| **Remote refs** | Any `http://` or `https://` URL |
| **External includes** | `<script src=…>`, `<link href=…>` |
| **Dynamic execution** | `eval()`, `new Function()`, `setTimeout("string")`, `setInterval("string")`, `import()`, `importScripts()` |
| **Persistence** | `localStorage`, `sessionStorage`, `indexedDB`, `serviceWorker` |
| **Download** (without exception) | `new Blob()`, `createObjectURL`, `revokeObjectURL` |
| **Clipboard** (without exception) | `navigator.clipboard` |

`navigator.clipboard.readText()` is **always** forbidden, even with the clipboard exception.

### B. Required markers

Every EDGE file must contain **all** of the following:

1. A `<meta>` CSP tag containing `connect-src 'none'`
2. The string `EDGE_ACTION_CONTRACT_V1`
3. The strings `Network: LOCKED`, `Persistence: NONE`, `Side Effects: NONE`
4. The string `EDGE_HARDENING_V1`
5. The string `EDGE_BUILD_ID`

All of these are provided by the hardening header snippet (`EDGE_HARDENING_HEADER_SNIPPET.html`).

### C. Policy exceptions

Only two exceptions exist. Declare them via HTML comments:

```html
<!-- EDGE_POLICY_EXCEPTION: download -->
<!-- EDGE_POLICY_EXCEPTION: clipboard -->
```

| Exception | What it allows | What stays blocked |
|---|---|---|
| `download` | `new Blob()`, `createObjectURL`, `revokeObjectURL`, download attribute | `http://`, `https://`, `fetch()`, all other network |
| `clipboard` | `navigator.clipboard.writeText()` | `navigator.clipboard.readText()` — always blocked |

Any other exception tag (e.g. `<!-- EDGE_POLICY_EXCEPTION: network -->`) causes an immediate **CI failure**.

---

## How to add a new EDGE file

1. Create `EDGE_YourModule_v1.html` in the repo root.
2. Copy the contents of `EDGE_HARDENING_HEADER_SNIPPET.html` into the file:
   - CSP meta tag → first child of `<head>`
   - Hardening shim script → in `<head>`, after the CSP tag
   - Action Contract block → in `<body>`, after the header
3. If your module uses blob downloads, add: `<!-- EDGE_POLICY_EXCEPTION: download -->`
4. If your module uses clipboard copy, add: `<!-- EDGE_POLICY_EXCEPTION: clipboard -->`
5. Set `EDGE_BUILD_ID` to a meaningful value (module name + version, or leave as `SET_ME` for development).
6. Run the linter locally before pushing (see below).

---

## How to run the linter locally

```bash
# From the repo root:
python tools/edge_lint.py

# Or point at a specific directory:
python tools/edge_lint.py --path edge/
```

The linter prints a per-file report and a summary:

```
[EDGE Lint] Scanning 3 EDGE file(s)...

  PASS  EDGE_Example_v1.html  [exceptions: download, clipboard]
  FAIL  EDGE_Broken_v1.html
        [L42] NETWORK: fetch()
        [file] MISSING: Hardening shim marker: EDGE_HARDENING_V1

────────────────────────────────────────────────────
  total_html_found:    5
  edge_files_scanned:  3
  failures:            2
  exceptions_used:     2
────────────────────────────────────────────────────
[EDGE Lint] FAIL — 1 file(s) with violations
```

Exit code `0` = pass, `1` = fail.

---

## Runtime defense (hardening shim)

In addition to the CI linter, every EDGE file includes a **runtime hardening shim** (`EDGE_HARDENING_V1`). This JavaScript block:

- Overrides `window.fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `navigator.sendBeacon`, `eval`, `window.open` with functions that throw errors
- Locks `localStorage`, `sessionStorage`, `indexedDB` via property descriptors
- Runs a self-check on `DOMContentLoaded` that halts the page if any `<script src=…>` or `<link href=…>` is detected

The shim is defense-in-depth. The CI linter is the primary enforcement gate.

---

## Design rationale

EDGE modules handle sensitive governance operations (key ceremonies, delegation proofs, credential derivation). They must:

- Run fully offline with no network calls
- Leave no persistent state on the host
- Include no external dependencies that could be supply-chain attacked
- Resist code injection via dynamic execution paths

The hardening policy makes these guarantees verifiable by both CI automation and human reviewers.
