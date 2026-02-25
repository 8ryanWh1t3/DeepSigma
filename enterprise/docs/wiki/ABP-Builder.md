# ABP Builder

> `build_abp.py` — constructs deterministic, self-authenticating Authority Boundary Primitives.

## Table of Contents

- [Overview](#overview)
- [build_abp()](#build_abp)
- [compose_abps()](#compose_abps)
- [write_abp()](#write_abp)
- [Verification Helpers](#verification-helpers)
- [CLI Usage](#cli-usage)
- [Embedding in HTML](#embedding-in-html)
- [Re-Stamping Procedure](#re-stamping-procedure)

---

## Overview

`build_abp.py` is the single source of truth for constructing ABP artifacts. It ensures:

- **Deterministic IDs** — same scope + authority_ref + created_at always produces same `abp_id`
- **Self-authenticating hashes** — content hash covers the entire ABP (with hash field zeroed)
- **Contradiction detection** — raises `ValueError` if any objective or tool appears in both allow and deny
- **Composition** — merges child ABPs into a parent with deduplication

**File:** `enterprise/src/tools/reconstruct/build_abp.py`

## build_abp()

Primary function for constructing a complete ABP v1 object:

```python
def build_abp(
    scope: dict,                          # contract_id, program, modules
    authority_ref: dict,                   # entry_id, entry_hash, ledger_path
    objectives: dict | None = None,       # {allowed: [], denied: []}
    tools: dict | None = None,            # {allow: [], deny: []}
    data: dict | None = None,             # {permissions: []}
    approvals: dict | None = None,        # {required: []}
    escalation: dict | None = None,       # {paths: []}
    runtime: dict | None = None,          # {validators: []}
    proof: dict | None = None,            # {required: []}
    delegation_review: dict | None = None,# {triggers: [], review_policy: {}}
    clock: str | None = None,             # ISO 8601 fixed timestamp
    effective_at: str | None = None,      # defaults to clock/now
    expires_at: str | None = None,        # null = no expiry
    parent_abp_id: str | None = None,     # parent ABP ID (composition)
    parent_abp_hash: str | None = None,   # parent ABP hash (composition)
) -> dict:
```

### Build sequence

1. Set `created_at` from `clock` or `datetime.now(UTC)`
2. Set `effective_at` from parameter or `created_at`
3. Assemble ABP dict with empty `abp_id` and `hash`
4. Conditionally include `delegation_review` (only when not None)
5. Compute `abp_id` = `_compute_abp_id(scope, authority_ref, created_at)`
6. Run `_check_contradictions(abp)` — raises `ValueError` on overlap
7. Compute `hash` = `_compute_abp_hash(abp)`
8. Return complete ABP dict

### Defaults

When optional sections are not provided:

| Section | Default |
|---------|---------|
| `objectives` | `{"allowed": [], "denied": []}` |
| `tools` | `{"allow": [], "deny": []}` |
| `data` | `{"permissions": []}` |
| `approvals` | `{"required": []}` |
| `escalation` | `{"paths": []}` |
| `runtime` | `{"validators": []}` |
| `proof` | `{"required": ["seal", "manifest", "pack_hash", "transparency_log", "authority_ledger"]}` |
| `delegation_review` | Key omitted entirely (not empty object) |

## compose_abps()

Merges multiple child ABPs into a parent:

```python
def compose_abps(
    parent_scope: dict,
    parent_authority_ref: dict,
    children: list[dict],
    clock: str | None = None,
    effective_at: str | None = None,
    expires_at: str | None = None,
) -> dict:
```

### Merge logic

| Section | Strategy |
|---------|----------|
| `objectives.allowed` | Concatenate from all children |
| `objectives.denied` | Concatenate from all children |
| `tools.allow` | Concatenate from all children |
| `tools.deny` | Concatenate from all children |
| `data.permissions` | Concatenate from all children |
| `approvals.required` | Concatenate from all children |
| `escalation.paths` | Concatenate from all children |
| `runtime.validators` | Concatenate from all children |
| `proof.required` | Union (sorted) |
| `delegation_review.triggers` | Deduplicate by trigger ID (first wins) |
| `delegation_review.review_policy` | Tightest `timeout_ms` wins |

After building the parent via `build_abp()`:

1. Inject `composition.children` with each child's `abp_id` + `hash`
2. Recompute parent hash (children change the canonical JSON)

## write_abp()

```python
def write_abp(abp: dict, out_dir: Path) -> Path:
```

Writes the ABP to `abp_v1.json` in the specified directory. Creates the directory if needed. Returns the output path.

Output format: `json.dumps(abp, indent=2) + "\n"`

## Verification Helpers

Three helper functions for verifying ABP artifacts:

```python
def verify_abp_hash(abp: dict) -> bool:
    """Recompute and verify content hash."""

def verify_abp_id(abp: dict) -> bool:
    """Recompute and verify ABP ID is deterministic."""

def verify_abp_authority(abp: dict, ledger_path: Path) -> bool:
    """Verify authority_ref exists and is not revoked in ledger."""
```

These are used by `verify_abp.py` and `gate_abp.py`.

## CLI Usage

```bash
python enterprise/src/tools/reconstruct/build_abp.py \
    --scope '{"contract_id":"CTR-DEMO-001","program":"SEQUOIA","modules":["hiring","bid","compliance","boe","award_staffing","coherence","suite_readonly","unified"]}' \
    --authority-entry-id AUTH-033059a5 \
    --authority-ledger enterprise/artifacts/public_demo_pack/authority_ledger.ndjson \
    --config abp_config.json \
    --clock 2026-02-25T00:00:00Z \
    --effective-at 2026-02-25T00:00:00Z \
    --out-dir edge/
```

### CLI Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--scope` | Yes | JSON scope object: `{contract_id, program, modules}` |
| `--authority-entry-id` | Yes | Authority ledger entry ID (e.g., `AUTH-033059a5`) |
| `--authority-ledger` | No | Path to authority ledger NDJSON |
| `--config` | No | JSON config with optional sections (objectives, tools, data, approvals, escalation, runtime, proof, delegation_review) |
| `--clock` | No | Fixed clock (ISO 8601 UTC) — deterministic timestamp |
| `--effective-at` | No | Effective date (defaults to clock) |
| `--expires-at` | No | Expiry date (defaults to null) |
| `--out-dir` | Yes | Output directory for `abp_v1.json` |

### Config File Format

The `--config` file provides optional ABP sections:

```json
{
    "objectives": {
        "allowed": [{"id": "OBJ-001", "description": "..."}],
        "denied": [{"id": "OBJ-D01", "description": "...", "reason": "..."}]
    },
    "tools": {
        "allow": [{"name": "seal_bundle", "scope": "DEC-001"}],
        "deny": [{"name": "authority_ledger_revoke", "reason": "..."}]
    },
    "data": {"permissions": [...]},
    "approvals": {"required": [...]},
    "escalation": {"paths": [...]},
    "runtime": {"validators": [...]},
    "proof": {"required": [...]},
    "delegation_review": {
        "triggers": [...],
        "review_policy": {...}
    }
}
```

### CLI Output

```
ABP written: edge/abp_v1.json
  abp_id:   ABP-bf0afe15
  hash:     sha256:c01f3565f11678598e098083ab01d7fc429d985525756300f932f44eea722789
  scope:    SEQUOIA / CTR-DEMO-001
  auth_ref: AUTH-033059a5
```

## Embedding in HTML

EDGE modules embed the ABP in a script block:

```html
<script type="application/json" id="ds-abp-v1">
{
  "abp_version": "1.0",
  "abp_id": "ABP-bf0afe15",
  ...
}
</script>
```

### Self-Verification JS

Each EDGE module includes `abpSelfVerify()` which:

1. Reads the ABP from the script block via `document.getElementById('ds-abp-v1')`
2. Parses the JSON
3. Computes the canonical hash using `abpCanonical()` (JavaScript equivalent of Python's `canonical_dumps()`)
4. Compares against the `hash` field
5. Updates `abpStatusBar` with the verification result

### Status Bar

```html
<div id="abpStatusBar">ABP: Verifying...</div>
```

After verification, displays one of:

- **ABP: VALID** (green) — hash matches
- **ABP: INVALID** (red) — hash mismatch
- **ABP: MISSING** (yellow) — no script block found

### Extracting Embedded ABP

To extract the ABP from an EDGE HTML file:

```python
import re
import json

html = open("edge/EDGE_Hiring_UI_v1.0.0.html").read()
pattern = r'<script\s+type=["\']application/json["\']\s+id=["\']ds-abp-v1["\']>\s*(.*?)\s*</script>'
match = re.search(pattern, html, re.DOTALL)
abp = json.loads(match.group(1))
print(json.dumps(abp, indent=2))
```

## Re-Stamping Procedure

When the ABP is updated (e.g., after a delegation review patch), all 8 EDGE exports must be re-stamped:

1. **Rebuild ABP** — run `build_abp.py` with updated config
2. **Write to reference** — output to `edge/abp_v1.json`
3. **Stamp each HTML** — replace the content between `<script id="ds-abp-v1">` and `</script>` with the new ABP JSON
4. **Gate check** — run `gate_abp.py --dir edge/ --abp-ref edge/abp_v1.json` to verify all 80 checks pass

Stamping script pattern:

```python
import re, json
from pathlib import Path

abp = json.loads(Path("edge/abp_v1.json").read_text())
abp_json = json.dumps(abp, indent=2)

for html_path in Path("edge").glob("EDGE_*.html"):
    html = html_path.read_text()
    html = re.sub(
        r'(<script\s+type=["\']application/json["\']\s+id=["\']ds-abp-v1["\']>)\s*.*?\s*(</script>)',
        rf'\1\n{abp_json}\n\2',
        html,
        flags=re.DOTALL,
    )
    html_path.write_text(html)
```
