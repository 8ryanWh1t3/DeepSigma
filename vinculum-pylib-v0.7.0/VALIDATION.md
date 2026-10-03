# Validation — VINCULUM pyLib v0.7.0

Release date: 2026-10-02. Real source baseline: v0.6.0, first rerun at 189 passing tests.

## Measured test runs

| Run | Passed | Skipped | Failures |
|---|---:|---:|---:|
| Current source | 305 | 1 | 0 |
| Installed wheel, outside source tree | 305 | 1 | 0 |
| Extracted delivery archive | 305 | 1 | 0 |

The one skipped test is actual Parquet decoding because pyarrow is unavailable. The missing-dependency path is separately tested. An attempted dependency install could not reach the package index due network/DNS access. No real Parquet success is claimed.

All 189 original baseline tests remain. All 14 original test files are byte-identical; 21 of 26 original Python modules are byte-identical. The other five carry version/exports changes. Fifteen new modules are added. Source/wheel parity checked every one of the 41 Python modules. See SEMANTIC_DELTA.json and validation/wheel-source-parity.json.

## Interpreter and dependencies

Executed on Python 3.13.5. Python >=3.10 is declared but a complete multi-version/OS matrix is not claimed. Version details are in validation/environment.json.

The wheel was actually installed into a new virtual environment and imported from that environment's site-packages, outside the source tree with PYTHONPATH unset. Third-party dependencies were shared from the preinstalled /opt/pyvenv site-packages through an explicit .pth because a nested --system-site-packages environment did not expose that parent virtual environment. This is package isolation and installed-wheel execution, not fresh network dependency resolution. See validation/installed-import.json.

## Synthetic stress result

Nine selected pairs: **3 ALIGNED, 1 PARTIAL, 4 CONFLICT, 0 UNRESOLVED, 1 NOT_COMPARABLE**. Four conflicts concern confidence, coverage, freshness and dependence. Zero detected objects remains distinct from zero actual objects. The scope comparison preserves a -40 percentage-point gap between expected100% and recorded60%; it is not a relative percent-change calculation.

The separate bakery extraction example resolves baker's dozen to13 and retains receipt12 / delta-1. Missing alignment support remains unknown. The cross-order coverage job normalizes a local SKOS label and pairs L1 with M4 after explicit mapping.

## Tested controls

Strict job/source schemas; duplicate JSON/YAML keys; unsafe YAML; source identity/hash mismatch; file-root confinement; bounded input; retained unresolved text; unit/interval failures; auto-pair global ambiguity on both endpoints; guided selection staging; cross-order and many-to-many choices; matching independent of observed agreement; ontology ambiguity/cycles; evidence roots/cycles/deep ancestry; missing ancestry; shared-root product protection; raw discrepancy unchanged by weak support; higher-order grouping; safe interval arithmetic; HTTP authentication and rejected paths/regex/configuration; archive idempotence and payload tampering; portable export manifest and inline replay.

The restricted arithmetic tests include rejection of calls, attributes, executable syntax and denominator intervals containing zero. This is not a comprehensive security certification.

## Artifact checks

- Offline HTML inspected in Chromium at1440px desktop and390px mobile. No page errors, external requests or executable scripts; no document-level horizontal overflow. Local-file navigation was unavailable, so a fresh page used in-memory set_content. This does not claim a successful file:// navigation.
- Report PDF:2 pages rendered and visually inspected; no clipped text, overlaps or missing glyphs.
- XLSX:11 sheets; formula error scan matched0 cells. The source-input fixture preserved quantity12 and deliberately withheld a formula-derived value as unverified. Source, extraction and review surfaces are included. artifact_tool is host-optional and is not installed by the wheel.
- Demo output manifest:17 entries verified, including PDF and XLSX.
- Benchmark: one local synthetic1000-pair run;200 planned conflicts observed. Timings recorded in validation/benchmark.json. This is not an operational scalability guarantee.

## Evidence files

validation/source-tests.xml and .txt; wheel-tests.xml and .txt; installed-import.json; wheel-source-parity.json; environment.json; browser.json; spreadsheet.json; artifact-qa.json; benchmark.json. Final archive test evidence is recorded externally as the delivery verification sidecar to avoid a self-referential archive hash.

## Explicitly unverified / application-owned

Real Parquet decoding; live Lattice/Foundry/Vantage/OnBase connections; unbounded natural-language understanding; OCR/visual document extraction; every file/application variant; unrestricted probability distributions; production IAM and network deployment; real sensor validation; Army endorsement; mission-command actions; operational safety certification.
