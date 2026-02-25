[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepsigma)](https://pypi.org/project/deepsigma/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

# DeepSigma

Institutional decision infrastructure: capture intent, run governed execution, detect drift, and patch safely.

## 60-Second Proof

```bash
pip install deepsigma
./run_money_demo.sh
```

Expected output:

```
BASELINE  score=90.00  grade=A
DRIFT     score=85.75  grade=B  red_flags=1
PATCH     score=90.00  grade=A  patch=RETCON  drift_resolved=true
```

**What just happened:**

1. **BASELINE** — scored an entity under a policy pack, produced a sealed episode
2. **DRIFT** — re-scored after a data change, detected coherence drift automatically
3. **PATCH** — applied a governed retcon patch, restored coherence, sealed the resolution

8 deterministic artifacts land in `docs/examples/demo-stack/drift_patch_cycle_run/`.
Every run produces the same scores, same grades, same artifacts — verify with:

```bash
make core-baseline   # SHA-256 proof in CORE_BASELINE_REPORT.json
```

## What It Does

> **Organizational coherence** is the ability to see, decide, and act as one system over time—because its truth, reasoning, and memory stay aligned across people, tools, and turnover.
>
> In practice, coherence means:
> - the "why" is retrievable (not tribal)
> - authority is explicit (not implied)
> - changes are patched, not overwritten
> - cross-team work links (people ↔ scope ↔ cost ↔ requirements)
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
