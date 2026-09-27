# pyAltCog v0.1.0 — Build Report

Build date: 2026-09-27

## Disposition

**PASS — initial library build validated.**

## Validation

- pytest: **40/40 passed**
- source compile: **PASS** (`python -m compileall -q src`)
- wheel build: **PASS**
- clean wheel install: **PASS**
- installed-wheel CLI demo: **PASS**
- demo maturity outcome: **AC6 Operational Alternative**
- demo score: **0.91**
- audit ledger verification: **PASS**
- mandatory runtime dependencies: **0**
- authored package files: **20**

## Wheel

`pyaltcog-0.1.0-py3-none-any.whl`

SHA-256: `149576a0c24dde104f284bad7c5a9a75038f3cd0e9d6d595df8c3e772d9c14c3`

## Canonical implementation scope

- AC0–AC8 maturity lifecycle
- seven discovery surfaces
- ALT-F13–ALT-F18 identifiers
- ALT-E13–ALT-E18 identifiers
- FSR / RER / ECC / ACP / DEP / DAM artifacts
- deterministic signal clustering
- deterministic discovery detectors
- optional offline hypothesis generation seam
- candidate scoring and operational promotion gates
- discriminating evidence / falsification plans
- dormant alternative archive/reactivation
- ADR / RCR / WPR / TAF / DAR metrics
- stable IDs + canonical hashing + hash-chained audit ledger
- neutral adapters for CERPA, DSAL/DKO, RESONATOR, PATHFINDER, IntelOps, ReOps, FranOps
- dependency-free CLI and examples

## Guardrail

Alternative **generation**, **discovery**, and **validation** remain separate. A generated hypothesis cannot promote itself to an Operational Alternative without evidence, a discriminating prediction, falsification condition, mission relevance, owner, revisit trigger, and promotion score.
