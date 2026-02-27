[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepsigma)](https://pypi.org/project/deepsigma/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Coherence Score](https://img.shields.io/badge/coherence-90%2F100-brightgreen)](./docs/metrics.md)

# DeepSigma

**DeepSigma prevents decision amnesia in AI systems.**

Log every agent decision. Detect when it drifts. Prove what happened.

## Quickstart

```bash
pip install deepsigma

# Log an agent decision
coherence agent log decision.json

# Audit all logged decisions
coherence agent audit --json

# Coherence score
coherence agent score
```

## 60-Second Proof

```bash
coherence demo
```

```
BASELINE   90.00 (A)
DRIFT      85.75 (B)   red=1
PATCH      90.00 (A)   patch=RETCON  drift_resolved=true
```

Three states, deterministic every run:
1. **BASELINE** — sealed episode, coherence scored
2. **DRIFT** — data changed, drift detected automatically
3. **PATCH** — governed retcon applied, coherence restored

Machine-readable: `coherence demo --json`

## What It Does

DeepSigma is the institutional memory layer that makes AI decisions reconstructable.

Every agent decision becomes a sealed, hash-chained episode. Drift between decisions is detected automatically across 8 types. Authority is captured cryptographically, not implied. The full "why" is retrievable in under 60 seconds.

> In practice:
> - the "why" is retrievable (not tribal)
> - authority is explicit (not implied)
> - changes are patched, not overwritten
> - drift is detected early and corrected consistently

## Editions

One product line, one version, two editions:

- **CORE edition:** minimal, demo-first, deterministic (`pip install deepsigma`)
- **ENTERPRISE edition:** extended adapters, dashboards, and ops surfaces (repo-native under `enterprise/`)

Edition boundary ledger: `EDITION_DIFF.md`

## Operating Modes

### Core Mode

Use Core mode when you need fast adoption and low cognitive load.

Active Core surface at repo root:

- `run_money_demo.sh`
- `src/core/`
- `docs/examples/demo-stack/`
- `tests/test_money_demo.py`

### Enterprise Mode

Use Enterprise mode when you need connectors, dashboards, extended security, broader telemetry, and integration-heavy workflows.

Dependency note:
- `pip install "deepsigma[enterprise]"` installs enterprise runtime extras used by telemetry/radar tooling.
- Full enterprise code surfaces are repository-native under `enterprise/` and are run from source in this repo.

Enterprise surfaces are first-class under:

- [`enterprise/README.md`](enterprise/README.md)

Examples of parked modules:

- `enterprise/dashboard/`
- `enterprise/docker/`
- `enterprise/release_kpis/`
- `enterprise/schemas/`
- `enterprise/scripts/`
- `enterprise/src/` (non-core packages)
- `enterprise/docs/` (full enterprise docs)

Run the enterprise wedge:

```bash
make enterprise-demo
make test-enterprise
```

## Release Artifacts

Build both edition artifacts from one version line:

```bash
make release-artifacts
```

Outputs in `dist/`:
- `deepsigma-core-vX.Y.Z.zip`
- `deepsigma-enterprise-vX.Y.Z.zip`

## Full Platform References

For the full-platform docs and architecture map, use parked docs directly:

- `enterprise/docs/positioning/positioning_manifesto.md`
- `enterprise/docs/positioning/executive_briefing_one_page.md`
- `enterprise/docs/release/`
- `enterprise/docs/security/`
- `enterprise/docs/mermaid/`

## Repo Intent

- Keep root focused on a reliable first proof.
- Keep enterprise depth available without deleting capability.
- Expand from Core into Enterprise intentionally, not by drift.

## License

[MIT](LICENSE)
