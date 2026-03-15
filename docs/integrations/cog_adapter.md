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
```

## Python API

```python
from core.integrations.cog_adapter import (
    load_cog_bundle,
    cog_to_deepsigma,
    deepsigma_to_cog,
    write_cog_bundle,
    verify_cog_bundle,
    extract_replay_sequence,
    to_deepsigma_replay_record,
)

# Import
bundle = load_cog_bundle("bundle.json")
artifact = cog_to_deepsigma(bundle)

# Export
bundle = deepsigma_to_cog(artifact)
write_cog_bundle(bundle, "exported.json")

# Verify
result = verify_cog_bundle(bundle)
print(result["status"])  # "pass", "warn", or "fail"

# Replay
steps = extract_replay_sequence(bundle)
record = to_deepsigma_replay_record(bundle)
```

## Known Limitations

1. **JSON-only** — does not read/write the binary `.cog` container format
2. **No real cryptography** — uses SHA-256 content hashing only (no HMAC signatures, no PQC)
3. **No COG scripting** — does not execute `.cogs` scripts or bytecode
4. **No peer sync** — does not implement the COG wire protocol for mesh/gossip sync
5. **Proof chain is shallow** — generates a single bundle-seal entry, not a full hash chain

## Future Improvements

- Binary `.cog` format support (pack/unpack)
- Full proof chain with per-artifact hash entries
- COG wire protocol adapter for peer sync
- MCP tool integration for live bundle exchange
- Streaming import/export for large bundles
