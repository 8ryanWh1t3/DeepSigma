<p align="center">
  <img src="docs/assets/overwatch-logo.svg" alt="Σ OVERWATCH" width="160" />
</p>

<h1 align="center">Institutional Decision Infrastructure</h1>

<p align="center">
  <strong>Truth · Reasoning · Memory</strong><br/>
  The control plane that makes every institutional decision auditable, reproducible, and self-correcting.
</p>

<p align="center">
  <a href="START_HERE.md">🚀 Start Here</a> ·
  <a href="HERO_DEMO.md">🔁 Hero Demo (5 min)</a> ·
  <a href="canonical/">📜 Canonical Specs</a> ·
  <a href="NAV.md">🗺️ Full Navigation</a>
</p>

---

## What This Is

Most AI governance frameworks tell you **what to worry about**.
Σ OVERWATCH tells you **what to do** — at the artifact level, in real time.

Every decision flows through three primitives:

| Primitive | Artifact | Purpose |
|-----------|----------|---------|
| **Truth** | Decision Ledger Record (**DLR**) | Immutable audit log of every decision |
| **Reasoning** | Reasoning Scaffold (**RS**) | Structured argument map with weighted claims |
| **Memory** | Decision Scaffold (**DS**) + Memory Graph (**MG**) | Reusable templates + organizational knowledge |

When reality changes, **Drift** is detected. When drift exceeds tolerance, a **Patch** corrects it.
This is the **Drift → Patch loop**.

---

## Try It Now

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -r requirements.txt

# Score coherence across sample episodes
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Run the full pipeline: episodes → DLR → RS → DS → MG → report
python -m coherence_ops.examples.e2e_seal_to_report

# Ask IRIS: why did we make this decision?
python -m coherence_ops iris query --type WHY --target ep-001
```

👉 **Full walkthrough:** [`HERO_DEMO.md`](HERO_DEMO.md) — 8 steps, 5 minutes, every artifact touched.

---

## Repo Structure

```
DeepSigma/
├─ START_HERE.md        # ← You are here (front door)
├─ HERO_DEMO.md         # 5-minute end-to-end walkthrough
├─ NAV.md               # Full navigation index
├── canonical/          # Normative specs: DLR, RS, DS, MG, Prime Constitution
├── category/           # Category declaration + positioning
├── coherence_ops/      # Python library + CLI + examples
├── specs/              # JSON schemas (11 schemas)
├── examples/           # Episodes, drift events, demo data
├── llm_data_model/     # LLM-optimized canonical data model
├── docs/               # Extended docs (vision, integrations, IRIS, policy packs)
├── mermaid/            # 28+ architecture & flow diagrams
├── ontology/           # Triad, artifact relationships, drift model
├── runtime/            # Operational runbooks
├── metrics/            # Coherence SLOs
├── dashboard/          # React dashboard + mock API
├── adapters/           # MCP, OpenClaw, OpenTelemetry
├── engine/             # Compression, degrade ladder, supervisor
├── release/            # Release readiness checklist
└── roadmap/            # Quarterly milestones
```

---

## CLI Quick Reference

| Command | What It Does |
|---------|-------------|
| `python -m coherence_ops audit <path>` | Cross-artifact consistency audit |
| `python -m coherence_ops score <path> [--json]` | Coherence score (0–100, A–F) |
| `python -m coherence_ops mg export <path> --format=json` | Export Memory Graph |
| `python -m coherence_ops iris query --type WHY --target <id>` | IRIS: why this decision? |
| `python -m coherence_ops iris query --type WHAT_DRIFTED --json` | IRIS: what drifted? |
| `python -m coherence_ops demo <path>` | Score + IRIS status in one command |

---

## Key Links

| Resource | Path |
|----------|------|
| Front door | [`START_HERE.md`](START_HERE.md) |
| Hero demo | [`HERO_DEMO.md`](HERO_DEMO.md) |
| Canonical specs | [`/canonical/`](canonical/) |
| JSON schemas | [`/specs/`](specs/) |
| Python library | [`/coherence_ops/`](coherence_ops/) |
| LLM data model | [`/llm_data_model/`](llm_data_model/) |
| IRIS docs | [`docs/18-iris.md`](docs/18-iris.md) |
| Navigation index | [`NAV.md`](NAV.md) |
| Docs map | [`docs/99-docs-map.md`](docs/99-docs-map.md) |
| Release checklist | [`release/CHECKLIST_v1.md`](release/CHECKLIST_v1.md) |

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). All contributions must maintain consistency with Truth · Reasoning · Memory and the four canonical artifact types (DLR / RS / DS / MG).

## License

See [`LICENSE`](LICENSE).

---

<p align="center">
  <strong>Σ OVERWATCH</strong><br/>
  We don’t sell agents. We sell the ability to trust them.
</p>
