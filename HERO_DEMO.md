# 🔁 Hero Demo: Decision → Seal → Drift → Patch → Memory

> **What:** Walk the complete Drift → Patch loop using real repo artifacts in under 5 minutes.
>
> **So What:** After this walkthrough you will understand how Institutional Decision Infrastructure works at the artifact level — not just the theory.

**Prerequisites:** Python 3.10+, repo cloned (`git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma`).

---

## Step 0: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 1: Inspect a Sealed Episode (Truth)

A sealed episode is a complete decision record — immutable once hashed. The repo ships four:

```bash
ls examples/episodes/
# 01_success.json
# 02_freshness_drift_abstain.json
# 03_time_drift_fallback.json
# 04_unsafe_action_blocked.json
```

Open the happy-path episode:

```bash
python -m json.tool examples/episodes/01_success.json | head -40
```

📖 **What you see:** A `DecisionEpisode` with a DTE (Decision Timing Envelope), outcome, verification results, and a seal hash. This is the **DLR** in action — the immutable audit log.

---

## Step 2: Run a Coherence Audit (Reasoning)

The CLI runs the full DLR → RS → DS → MG pipeline and scores coherence:

```bash
python -m coherence_ops audit ./coherence_ops/examples/sample_episodes.json
```

**Expected output (abbreviated):**

```
━━━ Coherence Audit ━━━
Manifest:  coherence_ops v0.2.0
Episodes:  3 loaded
DLR:       3 records built
RS:        1 session, 3 episodes ingested
DS:        drift signals collected
MG:        3 episodes, edges linked

Checks:
  ✓ DLR covers all episodes
  ✓ RS references valid DLR IDs
  ✓ MG provenance chain intact
  ✗ DS has unresolved red drift (1 signal)

Result: 3/4 checks passed
```

🧠 **What you see:** The **Reasoning Scaffold** validates that every claim, counter-claim, and evidence link forms a coherent chain. The audit catches the unresolved red drift signal.

---

## Step 3: Score Coherence (0–100)

```bash
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json
```

**Expected output:**

```json
{
  "overall_score": 72,
  "grade": "C",
  "dimensions": {
    "dlr_coverage": 95,
    "rs_completeness": 80,
    "ds_resolution": 45,
    "mg_connectivity": 70
  },
  "top_issues": [
    "1 unresolved red drift signal (bypass_drift)",
    "MG missing patch edge for ep-003"
  ]
}
```

📋 **What you see:** A quantified coherence score broken down by the four artifacts. The DS (Drift Signal) dimension drags the score down because there’s an unresolved drift.

---

## Step 4: Examine Drift Events (Drift Detection)

```bash
ls examples/drift/
# bypass_drift.json
# freshness_drift.json
# time_drift.json
```

Inspect the red-severity drift:

```bash
python -m json.tool examples/drift/bypass_drift.json
```

📋 **What you see:** A drift event with `severity: red`, a fingerprint, and a reference to the original sealed episode whose assumptions no longer hold. This is the **Drift** primitive firing.

---

## Step 5: Query with IRIS (Why Did This Happen?)

IRIS is the operator query engine. Ask it why:

```bash
python -m coherence_ops iris query --type WHY --target ep-001
```

**Expected output (abbreviated):**

```
IRIS Response: WHY ep-001
────────────────────
Summary: Episode ep-001 was a deployment decision governed by
         policy-pack "standard-deploy". All verification gates passed.

Provenance chain:
  [DLR]  dlr-001  (source)
  [RS]   rs-001   (analysis)
  [MG]   mg/ep-001 (memory)
```

Then check what drifted:

```bash
python -m coherence_ops iris query --type WHAT_DRIFTED --json
```

🧠 **What you see:** The **Memory Graph** answers operator questions in sub-60 seconds by tracing provenance chains across DLR → RS → DS → MG.

---

## Step 6: Run the End-to-End Pipeline (Full Loop)

This script runs the complete pipeline: sealed episodes → DLR → RS → DS → MG → CoherenceReport:

```bash
python -m coherence_ops.examples.e2e_seal_to_report
```

**Expected output (abbreviated):**

```
=== Example 1: Happy Path ===
  Coherence: 92/100 (A)
  DLR: 3 records | RS: 1 session | DS: 0 red signals | MG: 9 nodes

=== Example 2: Mixed Path ===
  Coherence: 68/100 (D)
  Drift signals: 3  |  By severity: {green: 1, yellow: 2}

=== Example 3: Stress Path ===
  Coherence: 41/100 (F)
  Drift signals: 5  |  By severity: {green: 1, yellow: 2, red: 2}
  Top drift fingerprint: bypass-gate (3 occurrences)
```

🔁 **What you see:** Three scenarios demonstrating how coherence scores degrade as drift accumulates — and how the system detects it automatically.

---

## Step 7: Export the Memory Graph

```bash
python -m coherence_ops mg export ./coherence_ops/examples/ --format=json
```

This outputs the full provenance graph as JSON. Alternatives:

```bash
# GraphML (for Gephi / yEd)
python -m coherence_ops mg export ./coherence_ops/examples/ --format=graphml

# Neo4j CSV (for graph database import)
python -m coherence_ops mg export ./coherence_ops/examples/ --format=neo4j-csv
```

📊 **What you see:** The **Memory Graph** exported as a portable graph — every episode, drift event, and patch connected by provenance edges.

---

## Step 8: Ship-It Demo (The One-Liner)

```bash
python -m coherence_ops demo ./coherence_ops/examples/sample_episodes.json
```

This runs score + IRIS status in one command. Use `--json` for machine-readable output.

---

## What Just Happened

You walked the complete **Drift → Patch loop**:

| Step | Primitive | Artifact | CLI Command |
|------|-----------|----------|-------------|
| 1 | Truth | DLR (sealed episode) | `cat examples/episodes/01_success.json` |
| 2 | Reasoning | RS (coherence audit) | `python -m coherence_ops audit ...` |
| 3 | Reasoning | Coherence Score | `python -m coherence_ops score ...` |
| 4 | Drift | DS (drift events) | `cat examples/drift/bypass_drift.json` |
| 5 | Memory | MG (IRIS query) | `python -m coherence_ops iris query ...` |
| 6 | Full Loop | All four artifacts | `python -m coherence_ops.examples.e2e_seal_to_report` |
| 7 | Memory | MG export | `python -m coherence_ops mg export ...` |
| 8 | Ship-it | Score + IRIS | `python -m coherence_ops demo ...` |

---

## Where to Go Next

| Goal | Resource |
|------|----------|
| Understand the canonical specs | [`/canonical/`](canonical/) — DLR, RS, DS, MG specifications |
| See the category claim | [`/category/declaration.md`](category/declaration.md) |
| Deep-dive on IRIS | [`docs/18-iris.md`](docs/18-iris.md) |
| Explore JSON schemas | [`/specs/`](specs/) |
| Browse Mermaid diagrams | [`/mermaid/`](mermaid/) |
| LLM-optimized data model | [`/llm_data_model/`](llm_data_model/) |
| Full docs index | [`docs/99-docs-map.md`](docs/99-docs-map.md) |
| Release checklist | [`release/CHECKLIST_v1.md`](release/CHECKLIST_v1.md) |

---

<p align="center"><strong>Σ OVERWATCH</strong> — Every decision auditable. Every drift detected. Every correction sealed.</p>
