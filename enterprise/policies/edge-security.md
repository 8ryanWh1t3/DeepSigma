# EDGE Security Policy

> Applies to all `EDGE_*.html` files in `edge/`, `enterprise/edge/`, and `core/edge/`.

## Core Principles

1. **Offline only.** EDGE modules run entirely in-browser with zero network access. CSP `connect-src 'none'` and runtime shim enforcement guarantee no data leaves the local machine.
2. **No persistence.** No localStorage, sessionStorage, indexedDB, or service workers. Ceremony data exists only in memory for the duration of the session.
3. **No external dependencies.** All code is inline. No `<script src>`, no `<link href>`, no CDN resources. Supply-chain attacks are structurally impossible.
4. **Defense in depth.** Both static analysis (CI linter) and runtime enforcement (hardening shim) block forbidden capabilities.

## Required Markers

Every EDGE file must contain all of the following:

| Marker | Purpose |
|---|---|
| `connect-src 'none'` | CSP meta tag blocking network |
| `EDGE_ACTION_CONTRACT_V1` | Action contract declaration |
| `Network: LOCKED` | Contract: no network |
| `Persistence: NONE` | Contract: no storage |
| `Side Effects: NONE` | Contract: no side effects |
| `EDGE_HARDENING_V1` | Runtime hardening shim present |
| `EDGE_BUILD_ID` | Module identity (must not be `SET_ME`) |

## Hardening Shim (v1.1)

The shim is a self-executing script that runs before any module code. It:
- Replaces network APIs (`fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`) with throwing stubs
- Blocks dynamic execution (`eval`, `Function` constructor)
- Blocks communication channels (`RTCPeerConnection`, `BroadcastChannel`, `SharedWorker`, `Worker`)
- Locks persistence APIs via property descriptors
- Locks `window.name` (covert data channel)
- Runs a DOMContentLoaded self-check for inline event handlers, external resources, base href hijacking, and meta refresh redirects

## Allowed Exceptions

Only two policy exceptions exist. Each must be declared via an HTML comment:

```html
<!-- EDGE_POLICY_EXCEPTION: clipboard -->
<!-- EDGE_POLICY_EXCEPTION: download -->
```

| Exception | Allows | Still Blocked |
|---|---|---|
| `clipboard` | `navigator.clipboard.writeText()` | `readText()` — always forbidden |
| `download` | `Blob`, `createObjectURL`, `revokeObjectURL` | All network APIs |

Any other exception tag causes CI failure.

## CI Enforcement

The linter (`tools/edge_lint.py`) runs on every push to `main` and every pull request via `.github/workflows/edge_lint.yml`.

**Scanned directories:** `edge/`, `enterprise/edge/`, `core/edge/`

**What it checks:**
- All forbidden patterns (network, dynamic exec, persistence, communication, HTML injection)
- Required markers present
- Exception tags valid
- Build ID not set to placeholder
- Multiline evasion patterns

**Exit code 0** = all files pass. **Exit code 1** = violations found, build fails.

## Adding a New EDGE Module

1. Create `EDGE_YourModule_v1.html` in the appropriate directory
2. Inject the hardening shim: `python tools/harden_inject.py yourfile.html`
3. Set `EDGE_BUILD_ID` to a meaningful value
4. Declare only needed exceptions
5. Run `python tools/edge_lint.py --path <directory>` locally before pushing

## Reference

Full policy details, threat model, and troubleshooting: see [README_EDGE_SECURITY.md](../../README_EDGE_SECURITY.md) at repo root.
