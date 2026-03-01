# EDGE Hardening Policy (v1.1)

Every `EDGE_*.html` module in this repository is a **self-contained, offline-only, zero-dependency** tool. This document describes the security policy enforced by CI and how to comply with it.

---

## What is enforced

The CI linter (`tools/edge_lint.py`) runs on every push to `main` and every pull request. It scans all `EDGE_*.html` files in the repo root and in `edge/`, and **fails the build** if any file violates the policy.

### A. Forbidden capabilities

| Category | Blocked patterns |
|---|---|
| **Network** | `fetch()`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon` |
| **Remote refs** | Any `http://` or `https://` URL |
| **External includes** | `<script src=...>`, `<link href=...>` |
| **Dynamic execution** | `eval()`, `new Function()`, `setTimeout("string")`, `setInterval("string")`, `import()`, `importScripts()` |
| **Persistence** | `localStorage`, `sessionStorage`, `indexedDB`, `serviceWorker` |
| **Communication** | `RTCPeerConnection`, `RTCDataChannel`, `mediaDevices`, `BroadcastChannel`, `SharedWorker`, `postMessage()`, `new Worker()` |
| **Exfiltration** | `window.name =` assignment |
| **HTML injection** | `<form action=...>`, `<meta http-equiv="refresh">`, `<base href=...>`, `<script type="importmap">` |
| **Download** (without exception) | `new Blob()`, `createObjectURL`, `revokeObjectURL` |
| **Clipboard** (without exception) | `navigator.clipboard` |

`navigator.clipboard.readText()` is **always** forbidden, even with the clipboard exception.

### B. Required markers

Every EDGE file must contain **all** of the following:

1. A `<meta>` CSP tag containing `connect-src 'none'`
2. The string `EDGE_ACTION_CONTRACT_V1`
3. The strings `Network: LOCKED`, `Persistence: NONE`, `Side Effects: NONE`
4. The string `EDGE_HARDENING_V1`
5. The string `EDGE_BUILD_ID` (set to a meaningful value, not `SET_ME`)

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

## Threat model

EDGE modules handle sensitive governance operations (key ceremonies, delegation proofs, credential derivation). The hardening policy defends against the following threat categories:

| Threat | Blocked by | Rationale |
|---|---|---|
| **Data exfiltration via network** | `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`, CSP `connect-src 'none'` | Sensitive ceremony data must never leave the local machine |
| **Supply-chain attack** | `<script src>`, `<link href>`, URL blocking | No external code can be loaded; all logic is inline |
| **Code injection** | `eval()`, `new Function()`, `setTimeout(string)`, `import()` | Dynamic execution paths are the primary injection vector |
| **Persistent state leakage** | `localStorage`, `sessionStorage`, `indexedDB`, `serviceWorker` | Ceremony artifacts must not persist on the host after the tab closes |
| **Peer-to-peer exfiltration** | `RTCPeerConnection`, `BroadcastChannel`, `SharedWorker`, `Worker`, `postMessage()` | WebRTC and cross-tab channels can bypass traditional network blocks |
| **Covert data channels** | `window.name` locking | `window.name` survives navigation and can exfiltrate data across origins |
| **HTML-level hijacking** | `<form action>`, `<meta refresh>`, `<base href>`, `<script type=importmap>` | Redirects and base-tag hijacking can reroute the page or its resources |

---

## How to add a new EDGE file

1. Create `EDGE_YourModule_v1.html` in the `edge/` directory.
2. Run the injection tool:
   ```bash
   python tools/harden_inject.py edge/EDGE_YourModule_v1.html --exceptions download clipboard
   ```
   Or manually copy from `EDGE_HARDENING_HEADER_SNIPPET.html`:
   - CSP meta tag as first child of `<head>`
   - Hardening shim script in `<head>`, after the CSP tag
   - Action Contract block in `<body>`, after the header
3. Set `EDGE_BUILD_ID` to a meaningful value (module name + version).
4. Declare only the exceptions your module actually needs.
5. Run the linter locally before pushing (see below).

---

## How to run the linter locally

```bash
# From the repo root:
python tools/edge_lint.py
python tools/edge_lint.py --path edge/

# JSON output (for CI artifacts or scripting):
python tools/edge_lint.py --json --path edge/

# Strict mode (fails on BUILD_ID=SET_ME warnings):
python tools/edge_lint.py --strict --path edge/
```

The linter prints a per-file report and a summary:

```text
[EDGE Lint] Scanning 3 EDGE file(s)...

  PASS  EDGE_Example_v1.html  [exceptions: download, clipboard]
  FAIL  EDGE_Broken_v1.html
        [L42] NETWORK: fetch()
        [file] MISSING: Hardening shim marker: EDGE_HARDENING_V1

----------------------------------------------------
  total_html_found:    5
  edge_files_scanned:  3
  failures:            2
  warnings:            0
  exceptions_used:     2
----------------------------------------------------
[EDGE Lint] FAIL — 1 file(s) with violations
```

Exit code `0` = pass, `1` = fail.

---

## How to upgrade the hardening shim

When the shim is updated (e.g. new blocked APIs), use the upgrade tool:

```bash
# Upgrade all EDGE files in edge/ and repo root:
python tools/shim_upgrade.py --all --root

# Upgrade specific files:
python tools/shim_upgrade.py edge/EDGE_MyModule_v1.html
```

The tool preserves existing `EDGE_BUILD_ID` values and policy exceptions.

---

## Runtime defense (hardening shim v1.1)

In addition to the CI linter, every EDGE file includes a **runtime hardening shim**. This JavaScript block:

- Overrides network APIs: `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`
- Blocks dynamic execution: `eval`, `Function` constructor
- Blocks navigation: `window.open`
- Blocks communication: `RTCPeerConnection`, `BroadcastChannel`, `SharedWorker`, `Worker`
- Locks persistence: `localStorage`, `sessionStorage`, `indexedDB` via property descriptors
- Locks data channels: `window.name` made read-only
- Logs build ID to console: `[EDGE] Hardening active: EDGE_BUILD_ID:...`
- Runs a DOMContentLoaded self-check that halts the page if it detects:
  - External `<script src>` or `<link href>` elements
  - Inline event handlers in the DOM
  - `<base href>` hijacking
  - `<meta http-equiv="refresh">` redirects

The shim is defense-in-depth. The CI linter is the primary enforcement gate.

---

## Troubleshooting

### Common linter errors

| Error | Cause | Fix |
|---|---|---|
| `MISSING: CSP meta: connect-src 'none'` | Hardening header not injected | Run `python tools/harden_inject.py yourfile.html` |
| `PERSISTENCE: localStorage` | Code uses `localStorage` directly | Replace with in-memory store (see `tools/edge_sanitize.py`) |
| `NETWORK: fetch()` | Code makes network requests | Remove or stub the fetch call |
| `REMOTE_REF: http(s):// URL` | Literal URL in source | URL-encode (`http%3A%2F%2F`) or use string concatenation for XML namespaces |
| `BUILD_ID: still set to SET_ME` | Build ID not configured | Set `EDGE_BUILD_ID` to module name + version |

### Browser console errors

If the runtime shim blocks an API call, you'll see:

```text
Error: EDGE hardening: fetch is blocked
```

This means your code is trying to use a forbidden API. Check the stack trace to find the caller and remove or replace the call.

### When to request exceptions

- **Download exception**: Your module generates files for the user to save (JSON exports, ceremony records, encrypted payloads). The download uses `Blob` + `createObjectURL` only — no network involved.
- **Clipboard exception**: Your module copies text to the clipboard for the user (fingerprints, hashes, ceremony records). Only `writeText()` is allowed; `readText()` is always blocked.

If neither of these covers your use case, the feature likely cannot be implemented within the EDGE security model.

---

## Design rationale

EDGE modules handle sensitive governance operations (key ceremonies, delegation proofs, credential derivation). They must:

- Run fully offline with no network calls
- Leave no persistent state on the host
- Include no external dependencies that could be supply-chain attacked
- Resist code injection via dynamic execution paths
- Block peer-to-peer and covert communication channels

The hardening policy makes these guarantees verifiable by both CI automation and human reviewers.
