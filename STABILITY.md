# Σ OVERWATCH — Stability Contract

**Version:** v0.3.2
**Status:** Alpha — no API stability guarantees before v1.0.0
**See also:** [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) · [CHANGELOG.md](CHANGELOG.md)

---

## Summary

DeepSigma v0.3.x is deployable alpha. The **artifact schemas** and **CLI entry points** are stable enough to build on. Internal Python module interfaces may change. Adapters are scaffolds. Nothing is frozen before v1.0.0.

If you depend on this project, pin to a specific commit or tag.

---

## What Is Stable Now (v0.3.x)

These interfaces are stable within the v0.3.x line — breaking changes will require a minor or major version bump and a CHANGELOG entry.

### 1. Artifact Schemas (JSON)

The canonical artifact shapes are stable. Once written, a sealed episode will be readable by future versions.

| Artifact | Schema File | Stability |
|----------|-------------|-----------|
| DecisionEpisode | `specs/episode.schema.json` | **Stable** |
| Decision Ledger Record (DLR) | `specs/dlr.schema.json` | **Stable** |
| Drift Event | `specs/drift.schema.json` | **Stable** |
| Decision Timing Envelope (DTE) | `specs/dte.schema.json` | **Stable** |
| Claim | `specs/claim.schema.json` | **Stable** |

The normative specifications in `canonical/` govern these schemas. A field will not be removed without a migration note in CHANGELOG.

### 2. CLI Entry Points

These CLI commands are stable and will not be renamed or removed without notice:

```bash
python -m coherence_ops score <path>
python -m coherence_ops audit <path>
python -m coherence_ops mg export <path>
python -m coherence_ops iris query --type <TYPE>
python -m coherence_ops demo <path>
```

The `coherence` console entry point is also stable (requires `pip install -e .`).

### 3. Money Demo Contract

The `drift_patch_cycle` demo must always produce:
- BASELINE grade A
- DRIFT grade B (or lower)
- PATCH grade A (restored)

This is enforced in `tests/test_money_demo.py`. Regression in this contract = release blocker.

### 4. Sample Data Corpus

The files in `examples/` and `coherence_ops/examples/` are stable reference data. They will not be removed (only extended) within v0.3.x.

---

## What Is Not Stable (v0.3.x)

Do not build hard dependencies on these — they may change between patch releases:

### Internal Python Classes and Methods

| Module | Status |
|--------|--------|
| `coherence_ops.dlr.DLRBuilder` | Internal — constructor kwargs may change |
| `coherence_ops.rs.ReflectionSession` | Internal — session API may evolve |
| `coherence_ops.scoring.CoherenceScorer` | Internal — dimension weights not frozen |
| `coherence_ops.audit.CoherenceAuditor` | Internal — finding format may change |
| `coherence_ops.iris.IRISEngine` | Internal — query resolution logic evolving |
| `engine.*` | Internal — compression/degrade/supervisor logic |

**Safe to use:** `CoherenceScorer.score()` return type (grade, overall, dimensions) is stable. Do not depend on exact float values of dimension scores.

### Adapter Implementations

| Adapter | Status |
|---------|--------|
| `adapters/mcp/` | **Scaffold** — not a full MCP implementation |
| `adapters/openclaw/` | **Alpha** — contract check logic stable, API may evolve |
| `adapters/otel/` | **Alpha** — span names and attributes may change |

### Dashboard

The React dashboard (`dashboard/`) is a demonstration UI. Its component API, data shapes, and server API (`dashboard/api_server.py`) are not stable interfaces.

### Coherence Scores

Exact numeric coherence scores are **not** stable — scorer weight tuning between releases may shift scores by a few points. Grade thresholds (A/B/C/D/F) are stable.

---

## Versioning Policy (Pre-1.0)

DeepSigma follows [Semantic Versioning](https://semver.org/) intent:

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| New stable feature, backward compatible | **minor** | 0.3.x → 0.4.0 |
| Bug fix, no interface change | **patch** | 0.3.1 → 0.3.2 |
| Breaking change to stable interface | **minor + CHANGELOG note** | 0.3.x → 0.4.0 |
| Pre-1.0 breaking change to unstable interface | **patch** (with CHANGELOG note) | 0.3.1 → 0.3.2 |

Until v1.0.0, **any release may change unstable interfaces without a major version bump**. The CHANGELOG will note all breaking changes.

### How Breaking Changes Are Communicated

1. Entry in [CHANGELOG.md](CHANGELOG.md) under `BREAKING` heading
2. Note in relevant canonical spec or doc
3. Migration path described if feasible

---

## v1.0.0 Criteria

v1.0.0 will be declared when all of the following are met:

| Criterion | Status |
|-----------|--------|
| All four artifact schemas pass round-trip validation | ✅ Done in v0.3.x |
| Money Demo contract passes on all 3 Python versions (3.10/3.11/3.12) | ✅ Done in v0.3.x |
| IRIS query latency ≤ 60s on standard corpus (SLO) | ✅ Met in v0.3.x |
| `CoherenceScorer` dimension weights frozen | ⏳ In progress |
| MCP adapter fully implements MCP protocol (not scaffold) | ⏳ Roadmap |
| `IRISEngine` public API frozen with typed signatures | ⏳ In progress |
| Test coverage ≥ 80% on `coherence_ops` package | ⏳ Target v0.4.x |
| Documentation: runbooks, cookbook, and API reference complete | ⏳ v0.3.2 ops-pack |

---

*See also: [CHANGELOG.md](CHANGELOG.md) · [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) · [roadmap/README.md](roadmap/README.md)*
