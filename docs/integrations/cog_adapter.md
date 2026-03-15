# COG Adapter

Integration adapter for [COG](https://cognis.work) portable cognition/proof bundles.

## What This Is

A clean adapter layer that allows Deep Sigma artifacts, receipts, and replay
structures to be **exported to** and **imported from** a COG-compatible JSON
bundle model. It maps Deep Sigma's five primitives (Truth, Reasoning, Memory,
Drift, Patch) to COG's four cognition planes (Memory, Behavior, Evolution, Proof).

## What This Is Not

- **Not a core primitive** — COG support is an integration adapter, not a sixth primitive
- **Not a binary format handler** — targets the JSON logical/semantic layer, not the binary `.cog` wire format
- **Not a COG runtime** — does not execute COG scripts, smart contracts, or blockchain operations
- **Not a replacement** for Deep Sigma's existing seal/hash infrastructure

## Mapping Tables

### Deep Sigma to COG

| Deep Sigma Primitive | COG Plane | COG Block Type | Artifact `refType` |
|---|---|---|---|
| Truth (Claims + Evidence) | Memory | `VEC_PAGES` | `evidence` |
| Reasoning (Decision Episode) | Behavior | `RULE_PACK` | `rationale` |
| Memory (Precedents + Graph) | Memory | `NEIGH_GRAPH` | `memory` |
| Drift (Drift Signals) | Evolution | `DIFF_STREAM` | `drift` |
| Patch (Corrections) | Behavior | `ADAPT_PATCH` | `patch` |
| Seal Hash (SHA-256) | Proof | `PROOF_CHAIN` | — |
| Replay Lineage | Behavior | `EVENT_LOG` | — |

### COG to Deep Sigma

| COG Element | Deep Sigma Target |
|---|---|
| Bundle manifest | `DeepSigmaDecisionArtifact.metadata` |
| Evidence artifacts | `truth_claims` list |
| Rationale artifacts | `reasoning` dict |
| Memory artifacts | `memory_refs` list |
| Drift artifacts | `drift_annotations` list |
| Patch artifacts | `patch_refs` list |
| Proof chain / signatures | `DeepSigmaReceipt.proof_metadata` |
| Replay steps | `DeepSigmaReplayRecord.steps` |

## CLI Usage

```bash
# Import a COG bundle
coherence cog import path/to/bundle.json
coherence cog import path/to/bundle.json --json

# Export a Deep Sigma artifact as a COG bundle
coherence cog export --artifact path/to/artifact.json output_bundle.json

# Verify a COG bundle
coherence cog verify path/to/bundle.json
coherence cog verify path/to/bundle.json --json

# Compare two bundles
coherence cog diff bundle_v1.json bundle_v2.json
coherence cog diff bundle_v1.json bundle_v2.json --json

# Batch import all bundles from a directory
coherence cog batch-import path/to/bundles/
coherence cog batch-import path/to/bundles/ --json

# Merge multiple bundles into one
coherence cog merge bundle1.json bundle2.json -o merged.json
coherence cog merge bundle1.json bundle2.json bundle3.json -o merged.json --json
```

## Python API

```python
from core.integrations.cog_adapter import (
    # Import
    load_cog_bundle, cog_to_deepsigma,
    stream_cog_artifacts, load_cog_bundle_metadata,
    # Export
    deepsigma_to_cog, write_cog_bundle,
    # Verify
    verify_cog_bundle,
    # Replay
    extract_replay_sequence, to_deepsigma_replay_record,
    # Proof Chain
    build_proof_chain, verify_proof_chain,
    # Diff
    diff_cog_bundles, CogBundleDiff,
    # Batch
    batch_import_cog_bundles, batch_export_deepsigma,
    filter_artifacts, merge_bundles, BatchImportResult,
)

# Import
bundle = load_cog_bundle("bundle.json")
artifact = cog_to_deepsigma(bundle)

# Export
bundle = deepsigma_to_cog(artifact)
write_cog_bundle(bundle, "exported.json")

# Verify (includes schema validation + proof chain verification)
result = verify_cog_bundle(bundle)
print(result["status"])  # "pass", "warn", or "fail"
print(result["proof_chain_valid"])  # per-artifact chain integrity
print(result["schema_valid"])  # JSON Schema validation

# Replay
steps = extract_replay_sequence(bundle)
record = to_deepsigma_replay_record(bundle)

# Proof Chain
chain = build_proof_chain(bundle.artifacts)
valid, errors = verify_proof_chain(chain)

# Diff
before = load_cog_bundle("v1.json")
after = load_cog_bundle("v2.json")
diff = diff_cog_bundles(before, after)
print(f"Added: {len(diff.added_artifacts)}")
print(f"Removed: {len(diff.removed_artifacts)}")
print(f"Modified: {len(diff.modified_artifacts)}")

# Streaming (iterator-based, pipeline-friendly)
for artifact_ref in stream_cog_artifacts("large_bundle.json"):
    print(artifact_ref.ref_id, artifact_ref.ref_type)

# Metadata-only (skip artifact parsing)
manifest, proof = load_cog_bundle_metadata("bundle.json")

# Batch import
result = batch_import_cog_bundles(["a.json", "b.json", "c.json"])
print(f"{result.succeeded}/{result.total} imported")

# Batch export
result = batch_export_deepsigma([artifact1, artifact2], "output_dir/")

# Filter
evidence_only = filter_artifacts(bundle, {"evidence", "rationale"})

# Merge
merged = merge_bundles([bundle1, bundle2])
write_cog_bundle(merged, "merged.json")
```

## JSON Schema Validation

COG bundles are validated against formal JSON Schemas at import time:

- `src/core/schemas/cog/cog_bundle.schema.json` — top-level bundle structure
- `src/core/schemas/cog/cog_artifact_ref.schema.json` — artifact ref with `refType` enum
- `src/core/schemas/cog/cog_proof.schema.json` — proof chain and signatures
- `src/core/schemas/cog/cog_replay_step.schema.json` — replay step structure

Schemas follow Draft 2020-12 and integrate with the existing `schema_validator.py` infrastructure.

## Per-Artifact Proof Chain

The exporter generates a **per-artifact hash chain** following the
`evidence_chain.py` pattern from `core.authority`:

- Each artifact gets a chain entry with `chainHash` (SHA-256 over entry fields)
  and `prevChainHash` (link to previous entry, `null` for first)
- The verifier walks the chain, re-computing each hash and checking links
- Legacy bundles with a single `bundle_seal` entry are still accepted

## MCP Tools

Five COG tools are registered in the MCP server scaffold:

| Tool | Description |
|---|---|
| `cog.import_bundle` | Import a COG bundle and return the mapped Deep Sigma artifact |
| `cog.export_artifact` | Export a Deep Sigma artifact as a COG bundle |
| `cog.verify_bundle` | Verify bundle integrity, proof chain, and schema |
| `cog.diff_bundles` | Compare two bundles for artifact-level differences |
| `cog.list_artifacts` | List artifacts with optional `refType` filter |

## Known Limitations

1. **JSON-only** — does not read/write the binary `.cog` container format
2. **No real cryptography** — uses SHA-256 content hashing only (no HMAC signatures, no PQC)
3. **No COG scripting** — does not execute `.cogs` scripts or bytecode
4. **No peer sync** — does not implement the COG wire protocol for mesh/gossip sync

## Future Improvements

- Binary `.cog` format support (pack/unpack)
- PQC signature support (infrastructure ready — `PQC` in GPE allowlist)
- COG wire protocol adapter for peer sync
- True streaming with `ijson` for very large bundles
