<div align="center">

# Institutional Decision Infrastructure

**Truth · Reasoning · Memory**

[🚀 Start Here](START_HERE.md) · [🔁 Hero Demo](HERO_DEMO.md) · [🏢 Boardroom Brief](category/boardroom_brief.md) · [📜 Specs](canonical/) · [🗺️ Navigation](NAV.md)

</div>

---

## The Problem

Your organization makes thousands of decisions. Almost none are structurally recorded with their reasoning, evidence, or assumptions.

- **Leader leaves** → their rationale leaves with them.
- **Conditions change** → nobody detects stale assumptions.
- **Incident occurs** → root-cause analysis becomes guessing.
- **AI accelerates decisions 100×** → governance designed for human speed fails silently.

This is not a documentation gap. It is a **missing infrastructure layer**.

Every institution pays this cost — in re-litigation, audit overhead, governance drag, and silent drift. The question: keep paying in consequences, or invest in prevention.

→ [Full economic tension analysis](category/economic_tension.md) · [Boardroom brief](category/boardroom_brief.md) · [Risk model](category/risk_model.md)

---

## The Solution

**Σ OVERWATCH** fills the void between systems of record and systems of engagement with a **system of decision**.

Every decision flows through three primitives:

| Primitive | Artifact | What It Captures |
|-----------|----------|------------------|
| **Truth** | Decision Ledger Record (DLR) | What was decided, by whom, with what evidence |
| **Reasoning** | Reasoning Scaffold (RS) | Why this choice — claims, counter-claims, weights |
| **Memory** | Decision Scaffold + Memory Graph (DS + MG) | Reusable templates + queryable institutional memory |

When assumptions decay, **Drift** fires.
When drift exceeds tolerance, a **Patch** corrects it.
This is the **Drift → Patch loop** — continuous self-correction.

---

## Try It (5 Minutes)

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -r requirements.txt

# Score coherence (0–100, A–F)
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Full pipeline: episodes → DLR → RS → DS → MG → report
python -m coherence_ops.examples.e2e_seal_to_report

# Why did we make this decision?
python -m coherence_ops iris query --type WHY --target ep-001
```

👉 Full walkthrough: [HERO_DEMO.md](HERO_DEMO.md) — 8 steps, every artifact touched.

---

## Repo Structure

```
DeepSigma/
├─ START_HERE.md          # Front door
├─ HERO_DEMO.md           # 5-min hands-on walkthrough
├─ NAV.md                 # Navigation index
├── category/             # Economic tension, boardroom brief, risk model
├── canonical/            # Normative specs: DLR, RS, DS, MG, Prime Constitution
├── coherence_ops/        # Python library + CLI + examples
├── specs/                # JSON schemas (11 schemas)
├── examples/             # Episodes, drift events, demo data
├── llm_data_model/       # LLM-optimized canonical data model
├── docs/                 # Extended docs (vision, IRIS, policy packs)
├── mermaid/              # 28+ architecture & flow diagrams
├── engine/               # Compression, degrade ladder, supervisor
├── dashboard/            # React dashboard + mock API
├── adapters/             # MCP, OpenClaw, OpenTelemetry
└── release/              # Release readiness checklist
```

---

## CLI Quick Reference

| Command | Purpose |
|---------|---------|
| `python -m coherence_ops audit <path>` | Cross-artifact consistency audit |
| `python -m coherence_ops score <path> [--json]` | Coherence score (0–100, A–F) |
| `python -m coherence_ops mg export <path> --format=json` | Export Memory Graph |
| `python -m coherence_ops iris query --type WHY --target <id>` | Why was this decided? |
| `python -m coherence_ops iris query --type WHAT_DRIFTED --json` | What assumptions decayed? |
| `python -m coherence_ops demo <path>` | Score + IRIS in one command |

---

## Key Links

| Resource | Path |
|----------|------|
| Front door | [START_HERE.md](START_HERE.md) |
| Hero demo | [HERO_DEMO.md](HERO_DEMO.md) |
| Boardroom brief | [category/boardroom_brief.md](category/boardroom_brief.md) |
| Economic tension | [category/economic_tension.md](category/economic_tension.md) |
| Risk model | [category/risk_model.md](category/risk_model.md) |
| Canonical specs | [/canonical/](canonical/) |
| JSON schemas | [/specs/](specs/) |
| Python library | [/coherence_ops/](coherence_ops/) |
| IRIS docs | [docs/18-iris.md](docs/18-iris.md) |
| Docs map | [docs/99-docs-map.md](docs/99-docs-map.md) |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions must maintain consistency with Truth · Reasoning · Memory and the four canonical artifacts (DLR / RS / DS / MG).

## License

See [LICENSE](LICENSE).

---

<div align="center">

**Σ OVERWATCH**
*We don't sell agents. We sell the ability to trust them.*

</div>
