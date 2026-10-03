# Migration - v0.6.0 -> v0.7.0

v0.7.0 does **not** require rewriting an existing `PairGraph` / `CrossOrderEngine` application. The canonical v0.6.0 comparison path remains valid.

## Stay on the direct graph path when

- your application already creates typed `Representation` objects;
- pair selection is already governed outside VINCULUM;
- you only need hinge/matrix/report evaluation.

## Adopt `VinculumPipeline` when

- you need bounded file/inline ingestion;
- you need explicit record-to-representation field mapping;
- you need source SHA-256 identity and evidence ancestry;
- you need declarative ontology normalization;
- you need batch pair planning/audit;
- you need replayable job fingerprints and multi-format review output;
- you want the optional API or local run archive.

## Behavioral invariants

The pipeline ultimately evaluates the same `PairGraph` through the same v0.6.0 `HingeEvaluator`. Pair status, raw discrepancy, and raw collision semantics therefore remain the comparison contract. New evidence and higher-order layers may withhold or qualify supported indicators, but they do not change a recorded delta into a different value.

## Version note

The attached concept diagrams use `v2.0` as a design label. Do not rename imports or package requirements to 2.0. The delivered release is `vinculum-pylib==0.7.0`.
