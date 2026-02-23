# Mermaid Diagrams (Canonical)

Nine diagrams define the visual language of Sigma OVERWATCH. Everything else is archived to reduce drift.

## Canonical Set

| # | Diagram | Type | Purpose |
|---|---------|------|---------|
| 01 | [System Architecture](01-system-architecture.md) | Graph | Where RAL sits between agents, data planes, observability, and Coherence Ops |
| 05 | [Drift to Patch](05-drift-to-patch.md) | Flowchart | 8 drift types → severity → fingerprint → 7 patch recommendations |
| 06 | [Coherence Ops Pipeline](06-coherence-ops-pipeline.md) | Graph + Pie | DLR / RS / DS / MG data flow through audit, scoring, and reconciliation |
| 10 | [Integration Map](10-integration-map.md) | Graph | Connectors, surfaces, and runtime integrations (MCP, LangChain, OTel, Foundry, Power Platform) |
| 11 | [Seal-and-Prove Pipeline](11-seal-and-prove.md) | Flowchart + State | Court-grade admissibility and transparency chain |
| 12 | [C-TEC Pipeline](12-c-tec-pipeline.md) | Flowchart | Time/Effort/Cost from deterministic telemetry with complexity weighting (Internal/Executive/DoD) |
| 13 | [Release Preflight Flow](13-release-preflight-flow.md) | Flowchart | Tag integrity gate before PyPI/GHCR publishing |
| 14 | [KPI Confidence Bands Flow](14-kpi-confidence-bands-flow.md) | Flowchart | KPI score + confidence/bands pipeline from evidence signals |
| 15 | [DISR Dual-Mode Architecture](15-disr-dual-mode-architecture.md) | Graph | Local default crypto provider with optional KMS plug-ins and authority controls |

## Archive

All other diagrams live in [`docs/archive/mermaid/`](../archive/mermaid/). They are preserved for reference but are not maintained as canonical.
See [`docs/archive/mermaid/ARCHIVE_INDEX.md`](../archive/mermaid/ARCHIVE_INDEX.md) for topic grouping.

## Adding New Diagrams

New diagrams require justification and must map to one of these canonical purposes:

1. **System poster** — high-level architecture
2. **Drift lifecycle** — detection, classification, patching
3. **Pipeline** — data flow through governance modules
4. **Integration** — connector and surface map
5. **Admissibility** — seal-and-prove and supply-chain integrity
6. **Release governance** — strict release/tag gates
7. **KPI telemetry** — scoring confidence and uncertainty bands
8. **DISR security architecture** — provider model + authority contracts

To add a diagram, update this index and ensure `tools/mermaid_audit.py` passes.
