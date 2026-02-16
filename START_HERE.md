# Σ OVERWATCH — Start Here

> **What:** Institutional Decision Infrastructure — the control plane that makes every institutional decision auditable, reproducible, and self-correcting.
>
> **So What:** If your org makes decisions that matter, this repo gives you the artifacts, schemas, and runtime to prove *what* was decided, *why*, and *what changed since*.

---

## The 60-Second Version

Every decision flows through three primitives:

| Primitive | Question | Artifact |
|-----------|----------|----------|
| **Truth** | What do we know? | Decision Ledger Record (**DLR**) |
| **Reasoning** | Why this choice? | Reasoning Scaffold (**RS**) |
| **Memory** | What did we learn? | Decision Scaffold (**DS**) + Memory Graph (**MG**) |

When reality shifts, **Drift** fires. When drift exceeds tolerance, a **Patch** corrects it.
This is the **Drift → Patch loop** — the system’s heartbeat.

```
DECIDE ──→ SEAL ──→ MONITOR ──→ DRIFT? ──→ PATCH ──→ MEMORY
  │                                                    │
  └────────────────── loop ─────────────────────┘
```

---

## Your Next 5 Minutes

| Step | Action | Time |
|------|--------|------|
| 1 | Read this page (done) | 60 sec |
| 2 | Run the **Hero Demo** — [`HERO_DEMO.md`](HERO_DEMO.md) | 4 min |
| 3 | Browse canonical specs — [`/canonical/`](canonical/) | when ready |

That’s the entire onramp.

---

## Repo Map (Where Things Live)

| You need… | Go to |
|------------|-------|
| Category claim & positioning | [`/category/`](category/) |
| Normative specs (DLR, RS, DS, MG) | [`/canonical/`](canonical/) |
| JSON schemas | [`/specs/`](specs/) |
| Python library + CLI | [`/coherence_ops/`](coherence_ops/) |
| End-to-end examples & episodes | [`/examples/`](examples/) |
| LLM-optimized data model | [`/llm_data_model/`](llm_data_model/) |
| Operational runbooks | [`/runtime/`](runtime/) |
| Extended docs (vision, integrations) | [`/docs/`](docs/) |
| Mermaid diagrams (28+) | [`/mermaid/`](mermaid/) |
| Dashboard UI | [`/dashboard/`](dashboard/) |
| Adapters (MCP, OpenClaw, OTel) | [`/adapters/`](adapters/) |
| Full navigation index | [`NAV.md`](NAV.md) |
| Docs de-duplication map | [`docs/99-docs-map.md`](docs/99-docs-map.md) |

---

## Key Files (The Fast Lane)

| File | What It Does |
|------|-------------|
| [`HERO_DEMO.md`](HERO_DEMO.md) | 5-minute walkthrough: Decision → Seal → Drift → Patch → Memory |
| [`canonical/dlr_spec.md`](canonical/dlr_spec.md) | Decision Ledger Record specification |
| [`canonical/rs_spec.md`](canonical/rs_spec.md) | Reasoning Scaffold specification |
| [`canonical/ds_spec.md`](canonical/ds_spec.md) | Decision Scaffold specification |
| [`canonical/mg_spec.md`](canonical/mg_spec.md) | Memory Graph specification |
| [`examples/sample_decision_episode_001.json`](examples/sample_decision_episode_001.json) | A complete sealed episode in JSON |
| [`coherence_ops/examples/e2e_seal_to_report.py`](coherence_ops/examples/e2e_seal_to_report.py) | Full pipeline: episode → coherence report |

---

## Glossary (Quick Reference)

| Term | Meaning |
|------|---------|
| **DLR** | Decision Ledger Record — immutable audit log |
| **RS** | Reasoning Scaffold — structured argument map |
| **DS** | Decision Scaffold — reusable decision template |
| **MG** | Memory Graph — organizational knowledge graph |
| **Drift** | When sealed assumptions no longer hold |
| **Patch** | Corrective DLR referencing the drifted original |
| **Sealed Episode** | Immutable, hashed decision record |
| **IRIS** | Query engine: WHY / WHAT_CHANGED / WHAT_DRIFTED / RECALL / STATUS |

Full glossary: [`GLOSSARY.md`](GLOSSARY.md)

---

<p align="center"><strong>Σ OVERWATCH</strong> — We don’t sell agents. We sell the ability to trust them.</p>
