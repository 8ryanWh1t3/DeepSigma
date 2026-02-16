<p align="center">
  <img src="docs/assets/overwatch-logo.svg" alt="Σ OVERWATCH" width="160" />
</p>

<h1 align="center">Institutional Decision Infrastructure</h1>

<p align="center">
  <strong>Truth · Reasoning · Memory</strong><br/>
  The control plane that makes every institutional decision auditable, reproducible, and self-correcting.
</p>

<p align="center">
  <img src="https://shields.io/badge/Category-Institutional_Decision_Infrastructure-blue" />
  <img src="https://shields.io/badge/Triad-Truth·Reasoning·Memory-green" />
  <img src="https://shields.io/badge/Loop-Drift→Patch-orange" />
</p>

---

## The Category in 60 Seconds

Most AI governance frameworks tell you **what to worry about**.
Σ OVERWATCH tells you **what to do** — at the artifact level, in real time.

Every institutional decision flows through three primitives:

| Primitive | Purpose | Artifact |
|-----------|---------|----------|
| **Truth** | What do we know right now? | **Decision Ledger Record (DLR)** — immutable log of every decision, claim, and evidence link |
| **Reasoning** | Why did we choose this? | **Reasoning Scaffold (RS)** — structured argument map with weighted claims and counter-claims |
| **Memory** | What did we learn? | **Decision Scaffold (DS)** + **Memory Graph (MG)** — reusable templates and organizational knowledge |

When reality changes, **Drift** is detected automatically.
When drift exceeds tolerance, a **Patch** is proposed, reviewed, and sealed.
This is the **Drift → Patch loop** — the heartbeat of institutional self-correction.

---

## Quickstart: Clone → Run Demo → Understand (< 3 min)

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git
cd DeepSigma

# 1. Read the category declaration
cat category/declaration.md

# 2. Walk the end-to-end demo
cat examples/demo_walkthrough.md

# 3. Inspect a sample sealed episode
cat examples/sample_decision_episode_001.json | python -m json.tool
```

**That's it.** You now understand Truth · Reasoning · Memory, and you've seen the Drift → Patch loop in action.

---

## The Four Core Artifacts

### 1. Decision Ledger Record (DLR)
The immutable audit log. Every decision gets a DLR that captures: who decided, what evidence was available, what claims were made, what outcome was chosen, and when it was sealed.

→ [Full Spec](canonical/dlr_spec.md) · [JSON Schema](specs/dlr.schema.json)

### 2. Reasoning Scaffold (RS)
The argument map. Before a decision is sealed, the RS lays out every claim, counter-claim, evidence link, and confidence weight — so reviewers can audit *why*, not just *what*.

→ [Full Spec](canonical/rs_spec.md) · [JSON Schema](specs/reasoning_scaffold.schema.json)

### 3. Decision Scaffold (DS)
The reusable template. Once a decision pattern works, the DS extracts it into a repeatable framework — like an Office template for institutional judgment.

→ [Full Spec](canonical/ds_spec.md) · [JSON Schema](specs/decision_scaffold.schema.json)

### 4. Memory Graph (MG)
The organizational brain. Every sealed episode feeds back into the MG, creating a living knowledge graph of what the institution has decided, learned, and corrected.

→ [Full Spec](canonical/mg_spec.md)

---

## The Drift → Patch Loop

```
  ┌─────────────────────────────────────────────┐
  │                                             │
  │   DECIDE ──→ SEAL ──→ MONITOR              │
  │     │                    │                  │
  │     │              drift detected?          │
  │     │                    │                  │
  │     │              yes ──┤──→ PATCH         │
  │     │                    │      │           │
  │     │                    │    review        │
  │     │                    │      │           │
  │     │                    │    seal          │
  │     │                    │      │           │
  │     └────── MEMORY ←────┘──────┘           │
  │                                             │
  └─────────────────────────────────────────────┘
```

1. **Decide** — Populate a DLR + RS with claims, evidence, and a chosen outcome.
2. **Seal** — Lock the episode with a cryptographic hash; it becomes immutable.
3. **Monitor** — Runtime checks compare current state to sealed assumptions.
4. **Drift** — When assumptions no longer hold, a drift event fires.
5. **Patch** — A new DLR is proposed to correct the drift, referencing the original.
6. **Memory** — The sealed correction feeds back into the Memory Graph.

→ [Drift-Patch Workflow](runtime/drift_patch_workflow.md) · [Sealing Protocol](runtime/sealing_protocol.md)

---

## Architecture

```
DeepSigma/
├── category/           # What category this creates and why
│   ├── declaration.md  # The category manifesto
│   └── positioning.md  # Competitive positioning & differentiation
├── canonical/          # The doctrine — normative specs for all artifacts
│   ├── prime_constitution.md
│   ├── dlr_spec.md
│   ├── rs_spec.md
│   ├── ds_spec.md
│   ├── mg_spec.md
│   └── unified_atomic_claims_spec.md
├── ontology/           # Conceptual model — triad, relationships, drift model
│   ├── triad.md
│   ├── artifact_relationships.md
│   └── drift_patch_model.md
├── runtime/            # Operational runbooks — how to execute the loop
│   ├── drift_patch_workflow.md
│   ├── sealing_protocol.md
│   └── encode_episode.md
├── metrics/            # Coherence SLOs and measurement
│   └── coherence_slos.md
├── roadmap/            # Quarterly milestones
│   └── README.md
├── examples/           # Working demos and sample data
│   ├── demo_walkthrough.md
│   └── sample_decision_episode_001.json
├── specs/              # JSON schemas for all artifacts
├── coherence_ops/      # Python library (DLR, RS, DS, MG)
├── docs/               # Extended documentation
└── wiki/               # Detailed reference pages
```

---

## Naming Guide

| Term | Abbreviation | Definition |
|------|-------------|------------|
| Decision Ledger Record | DLR | Immutable decision audit log |
| Reasoning Scaffold | RS | Structured argument map |
| Decision Scaffold | DS | Reusable decision template |
| Memory Graph | MG | Organizational knowledge graph |
| Truth · Reasoning · Memory | Triad | The three primitives |
| Drift | — | When sealed assumptions no longer hold |
| Patch | — | A corrective DLR that references the drifted original |
| Sealed Episode | — | An immutable, hashed decision record |
| Coherence SLO | — | Service-level objective for decision quality |

---

## Who This Is For

- **Compliance officers** who need auditable decision trails
- **AI/ML teams** who need reproducible reasoning chains
- **Enterprise architects** who need a decision control plane
- **Risk managers** who need drift detection before failures compound
- **Anyone** who has said: "Why did we decide that, and would we decide it the same way today?"

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. All contributions must maintain consistency with the Truth · Reasoning · Memory triad and the four canonical artifact types.

## License

See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Σ OVERWATCH</strong><br/>
  We don't sell agents. We sell the ability to trust them.
</p>
