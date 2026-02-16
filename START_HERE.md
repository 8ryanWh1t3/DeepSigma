# Σ OVERWATCH — Start Here

**What:** Institutional Decision Infrastructure — the control plane that makes every institutional decision auditable, reproducible, and self-correcting.

**So What:** If your org makes decisions that matter, this repo gives you the artifacts, schemas, and runtime to prove what was decided, why, and whether the reasoning still holds.

---

## If Your Lead Architect Left Tomorrow…

Your senior architect approved a critical deployment last quarter. They evaluated three vendors, weighed compliance against timeline pressure, and accepted specific technical trade-offs. None of this was structurally recorded. It lives in their head, a Slack thread, and a stale slide deck.

Now they're gone. Their replacement asks:

- Why did we choose this vendor?
- What constraints were active?
- Are those constraints still valid?

Nobody can answer confidently. The new architect either **freezes** (afraid to change what they don't understand) or **breaks something** (changing a decision whose dependencies they cannot see).

This is **institutional drift** — silent, compounding decay of decision quality that costs more every month it goes undetected.

Coherence Ops exists so that question has an instant, auditable answer — regardless of who asks or when.

→ [Full economic tension analysis](category/economic_tension.md)

---

## The 60-Second Version

Every decision flows through three primitives:

| Primitive | Question | Artifact |
|-----------|----------|----------|
| **Truth** | What do we know? | Decision Ledger Record (DLR) |
| **Reasoning** | Why this choice? | Reasoning Scaffold (RS) |
| **Memory** | What did we learn? | Decision Scaffold (DS) + Memory Graph (MG) |

When reality shifts, **Drift** fires. When drift exceeds tolerance, a **Patch** corrects it.
This is the **Drift → Patch loop** — the system's heartbeat.

```
DECIDE ──→ SEAL ──→ MONITOR ──→ DRIFT? ──→ PATCH ──→ MEMORY
│                                                         │
└────────────────── loop ─────────────────────┘
```

**Without this loop:** Drift accumulates silently. Remediation cost compounds. Mean time to detect a stale assumption: months or incidents.

**With this loop:** Drift caught at deviation. Remediation is a patch, not a crisis. Memory strengthens with every correction.

---

## Your Next 5 Minutes

| Step | Action | Time |
|------|--------|------|
| 1 | Read this page (done) | 60 sec |
| 2 | Run the [Hero Demo](HERO_DEMO.md) | 4 min |
| 3 | Browse [canonical specs](canonical/) | when ready |

That's the entire onramp.

---

## Repo Map

| You need… | Go to |
|------------|-------|
| Why this matters (economic) | [category/economic_tension.md](category/economic_tension.md) |
| Executive brief | [category/boardroom_brief.md](category/boardroom_brief.md) |
| Risk model | [category/risk_model.md](category/risk_model.md) |
| Normative specs (DLR, RS, DS, MG) | [/canonical/](canonical/) |
| JSON schemas | [/specs/](specs/) |
| Python library + CLI | [/coherence_ops/](coherence_ops/) |
| End-to-end examples | [/examples/](examples/) |
| LLM-optimized data model | [/llm_data_model/](llm_data_model/) |
| Operational runbooks | [/runtime/](runtime/) |
| Extended docs | [/docs/](docs/) |
| Full navigation | [NAV.md](NAV.md) |
| Docs de-duplication map | [docs/99-docs-map.md](docs/99-docs-map.md) |

---

## Key Files

| File | What It Does |
|------|-------------|
| [HERO_DEMO.md](HERO_DEMO.md) | 5-min walkthrough: Decision → Seal → Drift → Patch → Memory |
| [canonical/dlr_spec.md](canonical/dlr_spec.md) | Decision Ledger Record spec |
| [canonical/rs_spec.md](canonical/rs_spec.md) | Reasoning Scaffold spec |
| [canonical/ds_spec.md](canonical/ds_spec.md) | Decision Scaffold spec |
| [canonical/mg_spec.md](canonical/mg_spec.md) | Memory Graph spec |
| [examples/sample_decision_episode_001.json](examples/sample_decision_episode_001.json) | Complete sealed episode (JSON) |
| [coherence_ops/examples/e2e_seal_to_report.py](coherence_ops/examples/e2e_seal_to_report.py) | Full pipeline: episode → coherence report |

---

## Glossary

| Term | Meaning |
|------|---------|
| **DLR** | Decision Ledger Record — immutable audit log |
| **RS** | Reasoning Scaffold — structured argument map |
| **DS** | Decision Scaffold — reusable decision template |
| **MG** | Memory Graph — organizational knowledge graph |
| **Drift** | When sealed assumptions no longer hold |
| **Patch** | Corrective DLR referencing the drifted original |
| **IRIS** | Query engine: WHY / WHAT_CHANGED / WHAT_DRIFTED / RECALL / STATUS |

Full glossary: [GLOSSARY.md](GLOSSARY.md)

---

**Σ OVERWATCH** — *We don't sell agents. We sell the ability to trust them.*
