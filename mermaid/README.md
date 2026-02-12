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

## Diagram Types Used

- **graph** — directed graphs (architecture, dependencies)
- **sequenceDiagram** — interaction flows between components
- **erDiagram** — entity-relationship models
- **flowchart** — decision logic and data flow
- **stateDiagram** — state machines and lifecycles
- **mindmap** — hierarchical concept maps
- **pie** — proportional breakdowns

## Viewing

Click any `.md` file on GitHub to see the rendered diagrams.
Mermaid is supported natively — no extensions required.
