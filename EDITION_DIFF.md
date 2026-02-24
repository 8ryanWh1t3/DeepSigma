# DeepSigma Edition Contract

This file is the canonical boundary ledger between CORE and ENTERPRISE.

## Scope

- One product line, one version stream.
- Two editions:
  - CORE (default)
  - ENTERPRISE (optional surfaces)

## Source Layout Contract

- CORE code lives in:
  - `src/core/`
  - `src/coherence_ops/`
- ENTERPRISE code lives in:
  - `enterprise/src/`
  - `enterprise/dashboard/`
  - `enterprise/docs/`
  - `enterprise/scripts/`
  - `enterprise/release_kpis/`

## Packaging Contract

- Base install:
  - `pip install deepsigma`
- Enterprise extras install:
  - `pip install "deepsigma[enterprise]"`
  - Extras are dependency-focused; enterprise repo surfaces are run from source in `enterprise/`.

## Artifact Contract

- CORE artifact:
  - `dist/deepsigma-core-vX.Y.Z.zip`
- ENTERPRISE artifact:
  - `dist/deepsigma-enterprise-vX.Y.Z.zip`

## CI Contract

- CORE always-on gates:
  - `make edition-guard`
  - `make core-ci` (money demo + baseline + core tests)
- ENTERPRISE optional gate:
  - `make enterprise-ci` (enterprise demo + enterprise tests)
- Guardrail:
  - CORE must not import enterprise modules (`edition-guard`).

## Change Rules

- Changes that widen CORE scope must update this file.
- Any move of files between CORE and ENTERPRISE must update this file.
- CI gate changes must preserve CORE always-on and ENTERPRISE optional behavior unless explicitly versioned and approved.
