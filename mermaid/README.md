# Mermaid Diagrams

Visual documentation for **Σ OVERWATCH / RAL** and **Coherence Ops**.

GitHub renders Mermaid diagrams natively in `.md` files.

## Diagrams

| # | Diagram | Type | Description |
|---|---------|------|-------------|
| 01 | System Architecture | Graph | High-level view of where RAL sits in the agentic AI stack |
| 02 | Runtime Flow | Sequence | Request lifecycle: submit → context → plan → act → verify → seal |
| 03 | Schema Relationships | ER Diagram | Entity relationships between Episode, DTE, Action Contract, Drift |
| 04 | Degrade Ladder | Flowchart | Decision logic for fallback step selection |
| 05 | Drift to Patch | Flowchart | Drift detection → classification → patch recommendation lifecycle |
| 06 | Coherence Ops Pipeline | Graph + Pie | DLR/RS/DS/MG data flow and scoring weights |
| 07 | Policy Pack Lifecycle | State Diagram | Author → hash → load → verify → stamp → seal → audit |
| 08 | Module Dependencies | Graph | Python import dependency graph across all packages |
| 09 | AL6 Dimensions | Mindmap | The six dimensions of agentic reliability |
| 10 | Integration Map | Graph | Connections to MCP, OpenClaw, OTel, Foundry, Power Platform |
| 11 | Canonical Record Envelope | Graph | Structure of the universal record wrapper |
| 12 | Record Type Relationships | ER Diagram | How the 6 record types relate via graph edges |
| 13 | Provenance Chain | Flowchart | Claim → Evidence → Source trust chain + evidence tree |
| 14 | Seal & Patch Lifecycle | State Diagram | Record sealing, immutability, and patch flow |
| 15 | Retrieval Pipeline | Flowchart | Hybrid vector + keyword + graph query execution |
| 16 | Ingestion Flow | Flowchart | Legacy systems → connectors → canonical store |
| 17 | Data Lifecycle | State Diagram + Gantt | Active → expired → warm → archived → purged |
| 18 | Knowledge Graph Ontology | Graph | Node types, edge types, fraud investigation subgraph |
| 19 | Design Principles Cycle | Graph | Six design principles and their reinforcement loop |
| 20 | Validation Gate | Flowchart | Quality rules ingestion gate (QR-001 through QR-052) |
| 21 | Coherence Ops Alignment | Graph | DLR/RS/DS/MG → canonical record type mapping + scoring dimensions |
| 22 | Query Pattern Routing | Graph | 20 query patterns by caller role and retrieval method |
| 23 | Core 8 Ontology Graph | Graph | OWL classes + predicates from coherence_ops_core.ttl |
| 24 | SHACL Validation Gate | Flowchart | SHACL shape checks → conform/fail → seal or fix loop |
| 25 | SharePoint → RDF Pipeline | Flowchart | SP extraction → normalize → emit → validate → serve |
| 26 | Named Graph Sealing | State Diagram | Draft → sealed → drifted → patched immutability lifecycle |
| 27 | Claim Primitive | Graph + Mindmap + Flowchart + State | AtomicClaim structure, graph topology, truth types, status light derivation, seal lifecycle |
| 28 | DLR Claim-Native | Flowchart + Graph + ER + Graph | Decision flow, rationale graph, before/after comparison, entity relationships, composability hub |
| 30 | SharePoint Connector Flow | Flowchart | Graph API → field mapping → canonical record → ingest with delta sync and webhooks |
| 31 | Power Platform Connector Flow | Flowchart | Dataverse Web API → field mapping → canonical record + Power Automate trigger + reverse sync |
| 32 | LangChain Governance Flow | Sequence | Chain execution with GovernanceCallbackHandler DTE checks and violation decision tree |
| 33 | AskSage Connector Flow | Flowchart | AskSage API (query/train/datasets) → exhaust adapter → canonical records with auth token flow |
| 34 | Snowflake Connector Flow | Flowchart | Dual-mode Cortex AI + warehouse SQL → exhaust events → canonical records with shared auth |
| 35 | Connector Ecosystem | Graph | All v0.5.0 connectors with MCP tool counts, transport, and governance layer |
| 36 | Excel-First Governance | Flowchart + Sequence | Creative Director Suite architecture — BOOT protocol, named tables, LLM writeback, 6-lens model |
| 37 | MDPT Beta Kit | Flowchart | MDPT prompt lifecycle — Index → Catalog → Use → Log → Drift → Patch |
| 38 | Lattice Architecture | Graph | Credibility Engine claim lattice with Sync Plane and Credibility Index |
| 39 | Institutional Drift Loop | Flowchart | Drift → RootCause → Patch → MGUpdate → Seal → Index at institutional scale |

## Diagram Types Used

- `graph` — directed graphs (architecture, dependencies)
- - `sequenceDiagram` — interaction flows between components
  - - `erDiagram` — entity-relationship models
    - - `flowchart` — decision logic and data flow
      - - `stateDiagram` — state machines and lifecycles
        - - `mindmap` — hierarchical concept maps
          - - `pie` — proportional breakdowns
            - - `gantt` — timeline and lifecycle stages
             
              - ## Viewing
             
              - Click any `.md` file on GitHub to see the rendered diagrams. Mermaid is supported natively — no extensions required.
