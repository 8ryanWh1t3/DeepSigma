# Distributed Credibility Mesh — v1.0.0

> Multi-node credibility infrastructure with signed envelopes, federated quorum, and tamper-evident seal chains.

Abstract institutional credibility architecture. No real-world system modeled.

---

## What Is the Mesh?

The Distributed Credibility Mesh extends the Credibility Engine from a single-process runtime to a multi-node topology with:

- **Signed Evidence Envelopes** — Every evidence signal carries a payload hash and cryptographic signature
- **HTTP Replication** — Append-only logs replicate between nodes via push/pull
- **Federated Quorum** — Claims require multi-region, multi-group consensus to reach VERIFIED
- **Cross-Node Seal Verification** — Seal chains are mirrored and independently verifiable

## Node Roles

| Role | Responsibility |
|------|---------------|
| **Edge** | Generates signed evidence envelopes, replicates to peers |
| **Validator** | Verifies envelope signatures, emits ACCEPT/REJECT records |
| **Aggregator** | Computes federated claim state and credibility index |
| **Seal Authority** | Creates chained seals from aggregated state |

## Quick Start

```bash
# 1. Initialize mesh nodes (creates 7 nodes across 3 regions)
python -m mesh.cli init --tenant tenant-alpha

# 2. Run the full 4-phase scenario
python -m mesh.cli scenario --tenant tenant-alpha --mode day3

# 3. Verify envelope signatures and seal chains
python -m mesh.cli verify --tenant tenant-alpha
```

## Scenario Phases

| Phase | Name | What Happens |
|-------|------|-------------|
| 0 | Healthy | All regions online, low correlation, claims VERIFIED |
| 1 | Partition | Region B offline — quorum compresses, claim → UNKNOWN |
| 2 | Correlated Failure | Region C correlation INVALID — claim → DEGRADED |
| 3 | Recovery | Patch applied — regions restored, claims recover |

## Running Individual Phases

```bash
# Run only the healthy phase (3 cycles)
python -m mesh.cli run --tenant tenant-alpha --scenario healthy --cycles 3

# Run only the partition phase
python -m mesh.cli run --tenant tenant-alpha --scenario partition

# Run correlated failure
python -m mesh.cli run --tenant tenant-alpha --scenario correlated_failure

# Run recovery
python -m mesh.cli run --tenant tenant-alpha --scenario recovery
```

## Topology (Default)

```
Region A          Region B          Region C
─────────         ─────────         ─────────
edge-A            edge-B            edge-C
aggregator-A      validator-B       validator-C
seal-A
```

7 nodes, 3 regions. All nodes peer with each other for replication.

## Verification

```bash
python -m mesh.cli verify --tenant tenant-alpha
```

Checks:
- **Envelope signatures**: Every envelope's signature matches its payload hash
- **Seal chain continuity**: `prev_seal_hash` chains correctly; first seal uses `GENESIS`
- **Required fields**: `policy_hash` and `snapshot_hash` present in every seal

## Data Layout

```
data/mesh/{tenant_id}/{node_id}/
  ├── envelopes.jsonl          # Signed evidence envelopes
  ├── validations.jsonl        # Validator ACCEPT/REJECT records
  ├── aggregates.jsonl         # Federated aggregation snapshots
  ├── seal_chain_mirror.jsonl  # Seal chain entries
  ├── replication.jsonl        # Replication event log
  └── node_status.json         # Current node status
```

All JSONL files are append-only. Writes use atomic temp-file + rename.

## Crypto

| Priority | Backend | Notes |
|----------|---------|-------|
| 1 | `cryptography` (Ed25519) | Preferred; requires `pip install cryptography` |
| 2 | `pynacl` (Ed25519) | Alternative; requires `pip install pynacl` |
| 3 | HMAC-SHA256 (demo) | No external deps; labeled DEMO MODE in node status |

## API Endpoints

When the API server is running, mesh endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mesh/{tenant_id}/{node_id}/push` | POST | Push records to a node |
| `/mesh/{tenant_id}/{node_id}/pull` | GET | Pull records from a node |
| `/mesh/{tenant_id}/{node_id}/status` | GET | Node status |
| `/mesh/{tenant_id}/summary` | GET | Tenant mesh summary |

## Partition Detection and Recovery

`HTTPTransport` now tracks peer health as a simple state machine:

- `ONLINE` -> normal operation
- `SUSPECT` -> transient connectivity failures detected
- `OFFLINE` -> repeated failures beyond configured threshold

Recovery is automatic: once a peer starts responding again and reaches the
configured success threshold, it transitions back to `ONLINE`.

State thresholds and transport retry behavior are configurable:

- `max_retries`
- `backoff_base`
- `suspect_after_failures`
- `offline_after_failures`
- `recovery_successes`

`health()` output includes `peer_states` and `partition_metrics` for
partition/recovery visibility.

## Peer Identity and mTLS

`HTTPTransport` supports a node identity model (`NodeIdentity`) and mTLS policy
controls for peer-to-peer replication links.

- Identity uses a SPIFFE-style ID format:
  `spiffe://{trust_domain}/node/{node_id}`
- Optional peer certificate fingerprint checks can be configured per peer.
- mTLS policy can enforce:
  - HTTPS-only peer URLs
  - configured trust roots
  - client certificate and key paths
  - certificate rotation path metadata

Use `set_peer_identity`, `configure_trust_roots`, and
`rotate_client_certificate` to manage trust and rotation configuration.

## Guardrails

- Abstract institutional credibility model
- Non-domain: no real-world system modeled
- Mesh nodes cannot mutate history: seal → version → patch only
- Logs are append-only; no mutation or deletion via code paths
- Demo crypto mode clearly labeled when no Ed25519 library available
