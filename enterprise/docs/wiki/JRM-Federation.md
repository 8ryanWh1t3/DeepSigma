# JRM Federation

> Enterprise cross-environment coherence — gate validation, hub drift detection, advisory workflows, and packet signing.

## Overview

JRM Federation extends the core JRM pipeline with cross-environment coherence capabilities. Multiple SOC environments produce JRM-X packets independently; the federation layer ingests, validates, compares, and reconciles them.

**Modules**:
- `enterprise/src/deepsigma/jrm_ext/federation/gate.py` — packet validation and scope enforcement
- `enterprise/src/deepsigma/jrm_ext/federation/hub.py` — multi-env ingestion and drift detection
- `enterprise/src/deepsigma/jrm_ext/federation/advisory.py` — drift advisory lifecycle
- `enterprise/src/deepsigma/jrm_ext/security/signer.py` — HMAC-SHA256 packet signing
- `enterprise/src/deepsigma/jrm_ext/security/validator.py` — signature verification

## Architecture

```
SOC_EAST packets ──┐
                    ├→ JRMGate (validate + scope) → JRMHub (ingest + detect) → AdvisoryEngine
SOC_WEST packets ──┘                                    │
                                                         ├→ VERSION_SKEW
                                                         ├→ POSTURE_DIVERGENCE
                                                         └→ Federation Report
```

## Federation Gate

`JRMGate` validates packets before hub ingestion:

| Method | Purpose |
|--------|---------|
| `validate(packet_path)` | Check manifest integrity, required files present, SHA-256 hashes match |
| `enforce_scope(packet_path, allowed_envs)` | Reject packets from unauthorized environments |
| `redact(packet_path, redact_fields)` | Strip fields recursively, produce redacted zip |

Returns `GateResult` with `accepted`, `reason_code`, and `violations` list.

## Federation Hub

`JRMHub` aggregates packets from multiple environments:

| Method | Purpose |
|--------|---------|
| `ingest(packets)` | Load and index packets by environment |
| `detect_drift()` | Compare canon entries across environments |
| `merge_memory_graphs()` | Merge MG deltas into global graph |
| `produce_report()` | Generate federation summary JSON |

### Cross-Environment Drift Types

| Type | Detection | Threshold |
|------|-----------|-----------|
| `VERSION_SKEW` | Same signature_id, different active rev across envs | Any rev difference |
| `POSTURE_DIVERGENCE` | Same signature_id, different confidence across envs | Delta > 0.3 |
| `REFINEMENT_CONFLICT` | Incompatible patches across environments | Conflicting changes |

## Advisory Engine

`AdvisoryEngine` manages the drift advisory lifecycle:

| Method | Purpose |
|--------|---------|
| `publish(drifts)` | Create advisories from cross-env drift detections |
| `accept(advisory_id)` | Mark advisory as accepted |
| `decline(advisory_id)` | Mark advisory as declined |
| `list_advisories()` | List all advisories with current status |

Each advisory includes: `advisory_id`, `drift_type`, `source_env`, `target_envs`, `recommendation`, `status`.

## Packet Security

### Signing

`PacketSigner` uses HMAC-SHA256 with canonical JSON serialization:

```python
from deepsigma.jrm_ext.security.signer import PacketSigner

signer = PacketSigner("signing-key")
signature = signer.sign(manifest_data)
# {"algorithm": "hmac-sha256", "value": "<64-char hex>"}

assert signer.verify(manifest_data, signature) is True
```

Pluggable interface — subclass `PacketSigner` for KMS-backed signing.

### Validation

`PacketValidator` verifies signed packets:

```python
from deepsigma.jrm_ext.security.validator import PacketValidator

validator = PacketValidator("signing-key")
assert validator.validate(packet_zip_path) is True  # checks manifest signature
```

## Enterprise CLI

```bash
# Cross-environment federation report
deepsigma jrm federate --packets east/*.zip west/*.zip --out report.json

# Gate validation
deepsigma jrm gate validate --packet packet.zip

# Hub replay with drift detection
deepsigma jrm hub replay --packets east/*.zip west/*.zip --out hub_state.json

# Publish advisories from federation report
deepsigma jrm advisory publish --from report.json --out advisories.json
```

## Related Pages

- [JRM Pipeline](JRM-Pipeline) — core adapters, pipeline, and packet builder
- [Event Contracts](Event-Contracts) — routing table and function declarations
- [Security](Security) — threat model and authorization
