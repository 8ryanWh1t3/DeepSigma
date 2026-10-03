# Integration contract — v0.7.0

VINCULUM consumes mapped representations. Upstream systems own collection, domain interpretation and source access. Downstream systems own decisions, authority, state mutation and operational response.

## Python / CLI / notebooks

Import `VinculumPipeline`, load a declarative job, inspect the report and export it. Notebooks use the same ordinary Python API; no notebook server/plugin is installed.

The three command families are distinct:

- `vinculum`: preserved historical P/D heuristic API.
- `vinculum-lattice`: typed v0.6 cross-order scenario and event proposal APIs.
- `vinculum-pipeline`: v0.7 ingestion-to-output job API.

## API

Create an explicit FastAPI application with `create_app(token=...)`. POST JSON to `/v1/evaluate` using a bearer header. Responses use `vinculum.pipeline.result/1`. File-backed or regex-configured ingestion belongs in a trusted deployment-owned upstream process, not the public endpoint.

## LLM / codec

An LLM may be an upstream representation producer. It is not called by the package. Use declared source/target nodes and transformation links for codec preservation testing. A source's uncertainty faithfully preserved is different from meaning distorted by a generated summary.

## Graph and enterprise systems

Use native scenario JSON/Turtle or result RDF/JSON/CSV. The explicit local RDF/SKOS registry normalizes IDs; it does not turn ontology labels into physical truth. Preserve source IDs, domain definitions, units, population, denominator, time and scope when writing a connector.

Lattice/Foundry/Vantage/OnBase/A365 and PATHFINDER/RESONATOR/COMPOSER/Studio are integration targets only. No live connector or write authority is delivered. Excel exports are review artifacts, not automatic CERPA APPLY.

## Continuous monitoring

The retained `PairingMonitor` works with bounded in-memory normalized events and emits candidate proposals. The new `PairPlanner` handles batch-wide pairing selection. A host event loop, replay cursor, delivery transport, durable stream offsets, late-data policy and operational alerting remain application-owned.

## Review findings

Findings suggest REVIEW_DISCREPANCY, RESOLVE_OVERLAP, SUPPLY_MISSING_CONTEXT, REPAIR_PAIRING, ASSESS_SUPPORT, SELECT_PAIR, DEFINE_NUMERIC_MEANING or REVIEW_TRANSFORMATION. They are not mission commands, regulatory judgments or risk forecasts.
