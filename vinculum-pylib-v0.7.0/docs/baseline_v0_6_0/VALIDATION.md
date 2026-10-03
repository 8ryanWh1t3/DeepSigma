# Validation — VINCULUM pyLib v0.6.0

## Executed results

| Check | Measured result |
|---|---|
| Source suite | **189 passed; 0 failed; 0 errors; 0 skipped** |
| Installed-wheel suite | **189 passed; 0 failed; 0 errors; 0 skipped** |
| Extracted-delivery candidate suite | **189 passed; 0 failed; 0 errors; 0 skipped** |
| Retained baseline | **74 original regression cases; 10 test files unchanged** |
| Original functional modules | **9 byte-identical modules; __init__.py extended for version/exports** |
| Synthetic matrix demo | **9 selected pairs: 3 aligned, 1 partial, 4 conflicts, 1 not comparable** |
| Native JSON/Turtle roundtrip | **Report preserved in tests** |
| Generic Turtle field-map import | **Baker's-dozen conflict detected; ambiguous multi-values remain unpaired** |
| CLI from installed wheel | **Example runs and writes report artifacts** |
| HTML viewer | **In-memory Chromium render; 9 pair-detail sections; 0 page errors** |
| Desktop/mobile body overflow | **None at 1440 px / 390 px** |
| XLSX example | **6 sheets; expected counts 9/4/0/1/0; no cached formula errors** |
| Local smoke benchmark | **2,000 representations / 1,000 explicit pairs; 200 fixture conflicts** |

Python: **3.13.5**. RDFLib: **7.5.0**. A Python>=3.10 declaration is not a claim that every supported interpreter/OS combination was exercised.

The wheel was installed into a fresh virtual environment. Existing third-party dependencies were explicitly shared through a `.pth` file; this is not an independently downloaded, fully isolated dependency audit. `validation/wheel-import.json` confirms import from the installed wheel in the virtual environment, not the source tree.

The browser's direct `file://` navigation was blocked by this environment. The actual delivered HTML was loaded via `set_content` for rendering and DOM checks. This is an in-memory browser check, not a successful local-file-navigation claim.

The synthetic benchmark evaluated 1,000 selected pairs in **0.588 seconds** in one local run. This is not a production latency/scalability guarantee and does not substantiate million-object claims.

## Negative controls covered

Unpaired nodes; cross-order rather than diagonal-only pairing; higher orders; P/D on both sides; pair-local hinge P/D; missing factors; zero support; incompatible units; exact affine units; open thresholds; interval overlap; stale/misaligned time; different populations/denominators; unknown meanings; negation/qualification not discarded; ambiguous lexical rules; missing/shared/cyclic dependencies; duplicate pairs; repeated groups; codec uncertainty loss; unsupported additions; material omissions; stale codec snapshots; RDF projection tampering; strict JSON errors; HTML/CSV injection; monitor ambiguity, revisions, capacity and explicit eviction.

## Reproduce

```bash
python -m pip install .[test]
python -m pytest -q
python scripts/verify_manifest.py
vinculum-lattice evaluate examples/cross_order_scenario.json --out-dir out --summary
```

Machine-readable evidence is under `validation/`. `SEMANTIC_DELTA.json` contains the measured legacy module hashes. A final archive manifest and extracted-source rerun are checked again when producing the final ZIP.

## Limitations

No live sensor, Lattice, operational installation, external LLM, production repository or safety certification was involved. Semantic extraction is explicit-rule/adapter based. Reliability/support coefficients are not automatically calibrated probabilities. Theological narrative context is not scored. XLSX authoring requires the optional artifact_tool runtime; CSV, JSON and HTML are portable alternatives.

Wheel SHA-256: `1ac4ba1c7f90b29e60e2d26305b421960ed688b4df777ef1cb335872c14ffb83`
