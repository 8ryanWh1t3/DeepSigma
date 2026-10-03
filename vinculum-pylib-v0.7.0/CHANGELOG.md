# Changelog

## 0.7.0 - 2026-10-02

**Input -> Runtime -> Output integration over the verified v0.6.0 cross-order engine.**

Added:

- bounded source loaders and explicit extraction traces;
- `FieldMapping`-based representation construction;
- `OntologyRegistry` and evidence-source/ancestry registries;
- batch-wide `PairPlanner` with manual, guided, and named-policy unique one-to-one auto selection;
- higher-order support diagnostics kept separate from raw discrepancy/status;
- bounded exact/interval scalar arithmetic;
- review findings and replay fingerprints;
- portable JSON/CSV/Markdown/Turtle/offline-HTML exports plus optional PDF/XLSX adapters;
- optional authenticated FastAPI evaluation facade;
- optional local SQLite run archive;
- `vinculum-pipeline` CLI and replayable job schema;
- six attached architecture graphics recorded in `SOURCE_MANIFEST.json` and mapped in `GRAPHIC_TRACEABILITY.md`.

Preserved:

- v0.6.0 pair status and discrepancy semantics;
- pair-specific hinges only after pair selection;
- arbitrary cross-order `L_i <-> M_j` relationships;
- independent P/D channels on both language and mathematics representations;
- explicit separation of CONFLICT, PARTIAL, UNRESOLVED, NOT_COMPARABLE and unpaired material;
- v0.5.2 legacy API.

Measured semantic delta: **21/26 pre-existing v0.6.0 modules are byte-identical**. The core comparison modules (`core`, `hinge`, `math`, `lang`, `codec`, `monitor`, `rdf`, `serialization`) are unchanged. See `SEMANTIC_DELTA.md`.

Corrected from the attached concept graphics where necessary:

- `NOT_COMPARABLE` is not a synonym for `CONFLICT`;
- missing information is not false, zero, safe, or aligned;
- the 5x5 matrix is a space of possible order positions, not 25 automatic comparisons;
- a higher order is not automatically more certain;
- graphic `v2.0` labels are design labels, not the delivered package version;
- origin/retreat theology and cosmology remain non-scored context;
- no live Army/Foundry/Vantage/OnBase/Lattice connector or command action is claimed.

## 0.6.0 - 2026-10-02

Cross-order, pair-specific hinge and codec extension from the verified 0.5.2 package. Added typed order-aware representations, explicit arbitrary pairs, pair-local hinge states, typed comparability checks, interval mathematics, hierarchical aggregation, bounded pair proposals, codec preservation checks, JSON/Turtle scenarios, reporting, and non-scored narrative context.
