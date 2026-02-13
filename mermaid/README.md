# Mermaid Diagrams

Visual documentation for Σ OVERWATCH / RAL and Coherence Ops.
GitHub renders Mermaid diagrams natively in `.md` files.

## Diagrams

| # | Diagram | Type | Description |
|---|---------|------|-------------|
| 01 | [System Architecture](01-system-architecture.md) | Graph | High-level view of where RAL sits in the agentic AI stack |
| 02 | [Runtime Flow](02-runtime-flow.md) | Sequence | Request lifecycle: submit → context → plan → act → verify → seal |
| 03 | [Schema Relationships](03-schema-relationships.md) | ER Diagram | Entity relationships between Episode, DTE, Action Contract, Drift |
| 04 | [Degrade Ladder](04-degrade-ladder.md) | Flowchart | Decision logic for fallback step selection |
| 05 | [Drift to Patch](05-drift-to-patch.md) | Flowchart | Drift detection → classification → patch recommendation lifecycle |
| 06 | [Coherence Ops Pipeline](06-coherence-ops-pipeline.md) | Graph + Pie | DLR/RS/DS/MG data flow and scoring weights |
| 07 | [Policy Pack Lifecycle](07-policy-pack-lifecycle.md) | State Diagram | Author → hash → load → verify → stamp → seal → audit |
| 08 | [Module Dependencies](08-module-dependencies.md) | Graph | Python import dependency graph across all packages |
| 09 | [AL6 Dimensions](09-al6-dimensions.md) | Mindmap | The six dimensions of agentic reliability |
| 10 | [Integration Map](10-integration-map.md) | Graph | Connections to MCP, OpenClaw, OTel, Foundry, Power Platform |
| 11 | [Canonical Record Envelope](11-canonical-record-envelope.md) | Graph | Structure of the universal record wrapper |
| 12 | [Record Type Relationships](12-record-type-relationships.md) | ER Diagram | How the 6 record types relate via graph edges |
| 13 | [Provenance Chain](13-provenance-chain.md) | Flowchart | Claim → Evidence → Source trust chain + evidence tree |
| 14 | [Seal & Patch Lifecycle](14-seal-patch-lifecycle.md) | State Diagram | Record sealing, immutability, and patch flow |
| 15 | [Retrieval Pipeline](15-retrieval-pipeline.md) | Flowchart | Hybrid vector + keyword + graph query execution |
| 16 | [Ingestion Flow](16-ingestion-flow.md) | Flowchart | Legacy systems → connectors → canonical store |
| 17 | [Data Lifecycle](17-data-lifecycle.md) | State Diagram + Gantt | Active → expired → warm → archived → purged |
| 18 | [Knowledge Graph Ontology](18-knowledge-graph-ontology.md) | Graph | Node types, edge types, fraud investigation subgraph |
| 19 | [Design Principles Cycle](19-design-principles-cycle.md) | Graph | Six design principles and their reinforcement loop |
| 20 | [Validation Gate](20-validation-gate.md) | Flowchart | Quality rules ingestion gate (QR-001 through QR-052) |
| 21 | [Coherence Ops Alignment](21-coherence-ops-alignment.md) | Graph | DLR/RS/DS/MG → canonical record type mapping + scoring dimensions |
| 22 | [Query Pattern Routing](22-query-pattern-routing.md) | Graph | 20 query patterns by caller role and retrieval method |

## Diagram Types Used

- **graph** — directed graphs (architecture, dependencies)
- **sequenceDiagram** — interaction flows between components
- **erDiagram** — entity-relationship models
- **flowchart** — decision logic and data flow
- **stateDiagram** — state machines and lifecycles
- **mindmap** — hierarchical concept maps
- **pie** — proportional breakdowns
- **gantt** — timeline and lifecycle stages

## Viewing

Click any `.md` file on GitHub to see the rendered diagrams.
Mermaid is supported natively — no extensions required.
