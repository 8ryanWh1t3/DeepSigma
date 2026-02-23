# Mermaid Diagrams (Canonical)

Five diagrams define the visual language of Sigma OVERWATCH. Everything else is archived to reduce drift.

## Canonical Set

| # | Diagram | Type | Purpose |
|---|---------|------|---------|
| 01 | [System Architecture](01-system-architecture.md) | Graph | Where RAL sits between agents, data planes, observability, and Coherence Ops |
| 05 | [Drift to Patch](05-drift-to-patch.md) | Flowchart | 8 drift types → severity → fingerprint → 7 patch recommendations |
| 06 | [Coherence Ops Pipeline](06-coherence-ops-pipeline.md) | Graph + Pie | DLR / RS / DS / MG data flow through audit, scoring, and reconciliation |
| 10 | [Integration Map](10-integration-map.md) | Graph | Connectors, surfaces, and runtime integrations (MCP, LangChain, OTel, Foundry, Power Platform) |
| 12 | [C-TEC Pipeline](12-c-tec-pipeline.md) | Flowchart | Time/Effort/Cost from deterministic telemetry with complexity weighting (Internal/Executive/DoD) |

## Archive

All other diagrams live in [`docs/archive/mermaid/`](../archive/mermaid/). They are preserved for reference but are not maintained as canonical.

## Adding New Diagrams

New diagrams require justification and must map to one of the four canonical purposes:

1. **System poster** — high-level architecture
2. **Drift lifecycle** — detection, classification, patching
3. **Pipeline** — data flow through governance modules
4. **Integration** — connector and surface map

To add a diagram, update this index and ensure `tools/mermaid_audit.py` passes.
