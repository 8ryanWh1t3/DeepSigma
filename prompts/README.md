# Prompts Index

All versioned prompts in the DeepSigma repository.

---

## Canonical Prompts

Reusable analytical primitives — not tied to a specific workbook or tool.

| Prompt | File | Usage |
|--------|------|-------|
| Unified Executive Analysis | [`canonical/01_unified_executive_analysis.md`](canonical/01_unified_executive_analysis.md) | Structured decision output: executive summary, options comparison, failure modes, next actions |
| Executive Analysis (JSON) | [`canonical/01_unified_executive_analysis_json.md`](canonical/01_unified_executive_analysis_json.md) | JSON variant for automation pipelines |
| Reality Assessment | [`canonical/02_reality_assessment.md`](canonical/02_reality_assessment.md) | Perception correction: separate observable fact from narrative, check for drift and emotional bias |
| Reality Assessment (JSON) | [`canonical/02_reality_assessment_json.md`](canonical/02_reality_assessment_json.md) | JSON variant for automation pipelines |
| Decision Compression | [`canonical/04_decision_compression.md`](canonical/04_decision_compression.md) | Detect rushed decisions: compression risk scoring, decompression steps, cooling period |

---

## Prompt OS Control Prompts

Operational prompts for the Coherence Prompt OS v2 workbook.

| Prompt | File | Usage |
|--------|------|-------|
| START_SESSION A1 | [`prompt_os/START_SESSION_A1.md`](prompt_os/START_SESSION_A1.md) | Workbook triage: reads all tabs, surfaces top risks/actions, outputs structured format with seal |
| START_SESSION A1 (JSON) | [`canonical/03_multi_dim_prompting_for_teams_a1_json.md`](canonical/03_multi_dim_prompting_for_teams_a1_json.md) | JSON variant for automation pipelines |

> **Note:** `prompts/canonical/03_multi_dim_prompting_for_teams_a1.md` is a compatibility pointer to `START_SESSION_A1.md`. Use the Prompt OS file as the single source of truth.

---

## How to Use

1. **For standalone analysis** — use a canonical prompt (01 or 02) with your own context
2. **For compression checks** — use 04 before any high-stakes or rushed decision
3. **For workbook triage** — use the START_SESSION A1 prompt with the Prompt OS workbook attached
4. **For automation** — use the JSON variants (`*_json.md`) for machine-readable output

See [`docs/prompt_os/PROMPTS.md`](../docs/prompt_os/PROMPTS.md) for detailed usage notes and workbook tab mapping.
