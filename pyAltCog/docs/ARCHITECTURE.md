# pyAltCog Architecture

## Design intent

pyAltCog converts **unexplained friction** into **testable alternative cognition** without confusing creativity with evidence.

The engine separates three planes:

1. **Discovery** — reality produces evidence that the dominant model is incomplete.
2. **Generation** — one or more alternative explanations are formulated.
3. **Validation** — discriminating evidence tests which explanation survives.

That separation is the primary anti-speculation control.

## Canonical pipeline

```text
Observe
  ↓
Detect friction
  ↓
Cluster related signals
  ↓
Generate / register alternative hypothesis
  ↓
Discriminate dominant vs alternative predictions
  ↓
Score evidence + mission relevance
  ↓
Promote to AC6 only when operational gates pass
  ↓
Validate or reject
  ↓
Promote to AC7 OR archive to AC8 with reactivation trigger
```

## Determinism

The default library uses only deterministic transforms:

- normalized token sets;
- Jaccard similarity;
- deterministic connected-component clustering;
- explicit weighted scores;
- canonical JSON hashing;
- stable SHA-256-derived IDs;
- explicit state-transition guards.

Generative models can be attached outside the core through a provider, but an LLM-generated hypothesis still cannot promote itself. The evidence and lifecycle gates remain deterministic.

## Trust boundary

pyAltCog determines **candidate maturity**, not enterprise authority. Promotion to AC7 means the alternative won its defined validation path; it does not independently rewrite policy, doctrine, or institutional canon.

External authoritative mutation belongs to governed systems such as COMPOSER / CERPA / AuthorityOps.

## Integration seams

`pyaltcog.adapters` projects a candidate into neutral dictionaries suitable for:

- CERPA review/patch workflows;
- DSAL/DKO packaging;
- RESONATOR comparison/falsification cases;
- PATHFINDER graph relationships;
- IntelOps claims/evidence;
- ReOps decision episodes;
- FranOps canon-impact review.

These projections are intentionally one-way and dependency-free.
