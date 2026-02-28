# Mermaid Diagrams (Canonical)

Sixteen diagrams define the visual language of Sigma OVERWATCH. Everything else is archived to reduce drift.

## Canonical Set

| # | Diagram | Type | Purpose |
|---|---------|------|---------|
| 01 | [System Architecture](01-system-architecture.md) | Graph | Where RAL sits between agents, data planes, observability, and Coherence Ops |
| 05 | [Drift to Patch](05-drift-to-patch.md) | Flowchart | 8 drift types → severity → fingerprint → 7 patch recommendations |
| 06 | [Coherence Ops Pipeline](06-coherence-ops-pipeline.md) | Graph + Pie | DLR / RS / DS / MG data flow through AgentSession, audit, scoring, PRIME gate, CoherenceGate, IRIS, and MetricsCollector |
| 10 | [Integration Map](10-integration-map.md) | Graph | Connectors, surfaces, SDK packages, and runtime integrations (MCP, LangChain, OTel, Foundry, Power Platform) |
| 11 | [Seal-and-Prove Pipeline](11-seal-and-prove.md) | Flowchart + State | Court-grade admissibility and transparency chain |
| 12 | [C-TEC Pipeline](12-c-tec-pipeline.md) | Flowchart | Time/Effort/Cost from deterministic telemetry with complexity weighting (Internal/Executive/CustomerOrg) |
| 13 | [Release Preflight Flow](13-release-preflight-flow.md) | Flowchart | Tag integrity gate before PyPI/GHCR publishing |
| 14 | [KPI Confidence Bands Flow](14-kpi-confidence-bands-flow.md) | Flowchart | KPI score + confidence/bands pipeline from evidence signals |
| 15 | [DISR Dual-Mode Architecture](15-disr-dual-mode-architecture.md) | Graph | Local default crypto provider with optional KMS plug-ins and authority controls |
| 16 | [Authority Boundary Primitive](16-authority-boundary-primitive.md) | Flowchart + Graph | Pre-runtime ABP lifecycle: declare → build → attach → verify + composition model |
| 17 | [EDGE System](17-edge-system.md) | Flowchart + Graph | EDGE module map, gate enforcement flow, delegation review loop, Unified tab architecture |
| 18 | [SDK Package Architecture](18-sdk-package-architecture.md) | Graph | Three pip packages wrapping AgentSession with publish workflow |
| 19 | [FEEDS Pipeline](19-feeds-pipeline.md) | Graph | Five-stage event-driven pipeline: envelope → bus → ingest → consumers → canon |
| 20 | [Stability & Credibility Pipeline](20-stability-credibility-pipeline.md) | Flowchart | SSI, TEC sensitivity, security proof pack, and artifact kill-switch (v2.0.7) |
| 21 | [Scalability Benchmark Pipeline](21-scalability-benchmark-pipeline.md) | Flowchart | CI-eligible benchmark, regression gate, trend visualization, KPI integration (v2.0.8) |
| 22 | [Authority + Economic Evidence](22-authority-economic-evidence.md) | Flowchart | Authority custody, refusal contracts, evidence export, economic metrics uncapping (v2.0.9) |

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
9. **Authority boundaries** — pre-runtime governance declarations and composition
10. **EDGE surfaces** — exportable decision modules, gate enforcement, delegation review
11. **SDK packages** — standalone pip packages wrapping governance primitives for framework integration
12. **FEEDS pipeline** — event-driven pub/sub connecting governance primitives
13. **Stability & credibility** — nonlinear stability, economic sensitivity, security proof, artifact gates
14. **Scalability benchmark** — CI-eligible benchmark evidence, regression gate, trend visualization
15. **Authority + economic evidence** — custody lifecycle, refusal contracts, evidence export, economic metrics pipeline

To add a diagram, update this index and ensure `tools/mermaid_audit.py` passes.
