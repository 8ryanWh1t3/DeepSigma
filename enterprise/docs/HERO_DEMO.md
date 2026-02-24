---
title: "Hero Demo — Decision → Seal → Drift → Patch → Memory"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# 🔁 Hero Demo: Decision → Seal → Drift → Patch → Memory

**What:** Walk the complete Drift → Patch loop using real repo artifacts in under 5 minutes.
**So What:** After this walkthrough you understand how Institutional Decision Infrastructure works at the artifact level — not theory.

---

## Why This Demo Matters

Without sealing and drift detection, this exact scenario plays out:

1. A deployment decision is made. Reasoning lives in a meeting, a ticket, and a Slack emoji.
2. Six months later, the infrastructure assumptions behind that decision have changed — nobody knows.
3. Drift compounds silently. Downstream decisions build on the stale assumption.
4. When failure surfaces, the incident team traces backward and finds: gaps, missing reasoning, no provenance chain.

Every step below — sealing, auditing, scoring, drift detection, IRIS queries — prevents this scenario. The difference between an organization that can answer "why did we do this?" and one that cannot is exactly the infrastructure you are about to see.

---

**Prerequisites:** Python 3.10+, repo cloned (`git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma`).

## Step 0: Install Dependencies

```bash
pip install -r requirements.txt
```

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

📖 **What you see:** A DecisionEpisode with DTE (Decision Timing Envelope), outcome, verification results, and seal hash. This is the DLR in action — the immutable audit log.

## Step 2: Run a Coherence Audit (Reasoning)

```bash
python -m core audit ./core/examples/sample_episodes.json
```

Expected output:

```
━━━ Coherence Audit ━━━
Manifest:  core v0.2.0
Episodes:  3 loaded
DLR: 3 records built
RS:  1 session, 3 episodes ingested
DS:  drift signals collected
MG:  3 episodes, edges linked

Checks:
  ✓ DLR covers all episodes
  ✓ RS references valid DLR IDs
  ✓ MG provenance chain intact
  ✗ DS has unresolved red drift (1 signal)

Result: 3/4 checks passed
```

🧠 **What you see:** The Reasoning Scaffold validates every claim, counter-claim, and evidence link. The audit catches the unresolved red drift signal.

## Step 3: Score Coherence (0–100)

```bash
python -m core score ./core/examples/sample_episodes.json --json
```

Expected output:

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

📋 **What you see:** Coherence quantified across four artifacts. DS dimension drags the score down because of unresolved drift.

## Step 4: Examine Drift Events (Drift Detection)

```bash
ls examples/drift/
# bypass_drift.json  freshness_drift.json  time_drift.json

python -m json.tool examples/drift/bypass_drift.json
```

📋 **What you see:** A drift event with `severity: red`, a fingerprint, and a reference to the original sealed episode whose assumptions no longer hold. The Drift primitive firing.

## Step 5: Query with IRIS (Why Did This Happen?)

```bash
python -m core iris query --type WHY --target ep-001
```

Expected output:

```
IRIS Response: WHY ep-001
────────────────────
Summary: Episode ep-001 was a deployment decision governed
         by policy-pack "standard-deploy".
         All verification gates passed.

Provenance chain:
  [DLR] dlr-001 (source)
  [RS]  rs-001  (analysis)
  [MG]  mg/ep-001 (memory)
```

Then check what drifted:

```bash
python -m core iris query --type WHAT_DRIFTED --json
```

🧠 **What you see:** The Memory Graph answers operator questions in sub-60 seconds by tracing provenance chains across DLR → RS → DS → MG.

## Step 6: Run the End-to-End Pipeline (Full Loop)

```bash
python -m core.examples.e2e_seal_to_report
```

Expected output:

```
=== Example 1: Happy Path ===
Coherence: 92/100 (A)
DLR: 3 records | RS: 1 session | DS: 0 red signals | MG: 9 nodes

=== Example 2: Mixed Path ===
Coherence: 68/100 (D)
Drift signals: 3 | By severity: {green: 1, yellow: 2}

=== Example 3: Stress Path ===
Coherence: 41/100 (F)
Drift signals: 5 | By severity: {green: 1, yellow: 2, red: 2}
Top drift fingerprint: bypass-gate (3 occurrences)
```

🔁 **What you see:** Three scenarios showing how coherence degrades as drift accumulates — and how the system detects it automatically.

## Step 7: Export the Memory Graph

```bash
python -m core mg export ./core/examples/ --format=json

# Alternatives:
# GraphML (Gephi / yEd):    --format=graphml
# Neo4j CSV (graph DB):     --format=neo4j-csv
```

📊 **What you see:** The Memory Graph exported as a portable graph — every episode, drift event, and patch connected by provenance edges.

## Step 8: Ship-It Demo (One-Liner)

```bash
python -m core demo ./core/examples/sample_episodes.json
# Use --json for machine-readable output
```

---

## What Just Happened

You walked the complete Drift → Patch loop:

| Step | Primitive | Artifact | CLI Command |
|------|-----------|----------|-------------|
| 1 | Truth | DLR (sealed episode) | `cat examples/episodes/01_success.json` |
| 2 | Reasoning | RS (coherence audit) | `python -m core audit ...` |
| 3 | Reasoning | Coherence Score | `python -m core score ...` |
| 4 | Drift | DS (drift events) | `cat examples/drift/bypass_drift.json` |
| 5 | Memory | MG (IRIS query) | `python -m core iris query ...` |
| 6 | Full Loop | All four artifacts | `python -m core.examples.e2e_seal_to_report` |
| 7 | Memory | MG export | `python -m core mg export ...` |
| 8 | Ship-it | Score + IRIS | `python -m core demo ...` |

## Run the Money Demo

One command proves the full Drift → Patch loop with observable score changes:

```bash
python -m core.examples.drift_patch_cycle
```

**Expected output:**

```
BASELINE  90.00 (A)
DRIFT    85.75 (B)   red=1
PATCH    90.00 (A)   patch=RETCON  drift_resolved=true
Artifacts: examples/demo-stack/drift_patch_cycle_run/
```

Artifacts are written to [`examples/demo-stack/drift_patch_cycle_run/`](examples/demo-stack/drift_patch_cycle_run/) including three coherence reports, three memory graph snapshots, a diff, and a Mermaid diagram (`loop.mmd`).

---

## Where to Go Next

| Goal | Resource |
|------|----------|
| Canonical specs | [/docs/canonical/](canonical/) — DLR, RS, DS, MG specifications |
| Category claim | [/docs/category/declaration.md](category/declaration.md) |
| IRIS deep-dive | [18-iris.md](18-iris.md) |
| JSON schemas | [/schemas/](../schemas/) |
| Mermaid diagrams (canonical) | [`docs/mermaid/`](mermaid/) |
| Mermaid archive (historical) | [`docs/archive/mermaid/`](archive/mermaid/) |
| LLM-optimized data model | [/docs/llm_data_model/](llm_data_model/) |
| Full docs index | [99-docs-map.md](99-docs-map.md) |
| Release checklist | [release/CHECKLIST_v1.md](release/CHECKLIST_v1.md) |

---

**Σ OVERWATCH** — *Every decision auditable. Every drift detected. Every correction sealed.*
