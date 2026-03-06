# Artifact Builder Spec (Primitive 3)

## Purpose

Serialize compiled policies to inspectable JSON files on disk. Supports write, load, and seal verification.

## Module

`src/core/authority/artifact_builder.py`

## Artifact JSON Structure

```json
{
  "artifactId": "GOV-{12hex}",
  "sourceId": "PSRC-{12hex}",
  "dlrRef": "DLR-...",
  "episodeId": "EP-...",
  "policyPackId": "PP-...",
  "rules": [
    {
      "constraintId": "C-...",
      "constraintType": "requires_dlr",
      "expression": "dlr_ref IS NOT NULL",
      "parameters": {}
    }
  ],
  "reasoningRequirements": {
    "requirementId": "RR-...",
    "requiresDlr": true,
    "minimumClaims": 1,
    "requiredTruthTypes": [],
    "minimumConfidence": 0.7,
    "maxAssumptionAge": ""
  },
  "policyHash": "sha256:<hex>",
  "createdAt": "2026-03-06T...",
  "seal": {
    "hash": "sha256:<hex>",
    "sealedAt": "2026-03-06T...",
    "version": 1
  }
}
```

## Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `build_artifact` | `(compiled: CompiledPolicy) -> dict` | Convert to serializable dict with seal |
| `write_artifact` | `(compiled, output_dir: Path) -> Path` | Write `{artifact_id}.json` to disk |
| `load_artifact` | `(path: Path) -> dict` | Load + verify seal (raises `ValueError` if tampered) |
| `verify_artifact` | `(artifact: dict) -> bool` | Non-raising seal verification |

## Seal Verification

The seal hash is computed over the artifact body (everything except the `seal` key). On load, the body is re-hashed and compared against `seal.hash`. Tampered artifacts raise `ValueError`.
