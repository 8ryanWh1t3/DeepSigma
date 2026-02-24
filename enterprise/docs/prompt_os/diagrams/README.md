# Prompt OS v2 — Architecture Diagrams

## prompt_os_flow.mmd

Mermaid flowchart showing the data flow between all Prompt OS workbook tabs.

### Node Reference

| Node | Tab | Role |
|------|-----|------|
| **REALITY_ENGINE** | `REALITY_ENGINE` | Entry point: structured perception checks separate observable fact from narrative |
| **EXECUTIVE_ENGINE** | `EXECUTIVE_ENGINE` | Structured decision analysis with options comparison and failure modes |
| **DECISION_LOG** | `DECISION_LOG` | Decision memory: records what was decided, with evidence and scoring |
| **ATOMIC_CLAIMS** | `ATOMIC_CLAIMS` | Truth claim registry: individual assertions with credibility scoring |
| **ASSUMPTIONS** | `ASSUMPTIONS` | Assumption tracker: half-life decay model with expiry risk coloring |
| **PATCH_LOG** | `PATCH_LOG` | Corrective action log: drift events and patches with severity |
| **PROMPT_LIBRARY** | `PROMPT_LIBRARY` | Prompt asset registry: versioned prompts with health scoring and drift detection |
| **LLM_OUTPUT** | `LLM_OUTPUT` | Session capture: LLM-generated actions, risks, and seal hashes |
| **DASHBOARD_V2** | `DASHBOARD_V2` | Live KPI summary aggregating all tables |
| **DASHBOARD_TRENDS** | `DASHBOARD_TRENDS` | Weekly snapshot history for trend reporting |

### Data Flow

1. **Perception** → Reality Engine feeds observations into Executive Engine (decisions) and Atomic Claims (facts)
2. **Decision** → Executive Engine outputs go to Decision Log for persistent record
3. **Memory** → Claims feed Assumptions; Assumptions and Decisions feed Patch Log when drift is detected
4. **Governance** → Prompt Library drift also triggers patches
5. **LLM Sessions** → LLM Output feeds back into Decision Log and Atomic Claims
6. **Dashboard** → Dashboard V2 aggregates all tables; Dashboard Trends captures weekly snapshots

### Rendering

To render the diagram:

```bash
# Using Mermaid CLI
mmdc -i prompt_os_flow.mmd -o prompt_os_flow.svg

# Or view directly on GitHub (Mermaid is natively supported in .md files)
```
