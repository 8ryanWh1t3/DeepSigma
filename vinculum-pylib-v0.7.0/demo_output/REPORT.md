# VINCULUM pyLib 0.7.0
## When words and numbers collide.
Graph: **SYNTHETIC-CODEC-LIMIT-TEST**. Selected-pair status: **CONFLICT**.

This report evaluates representations. It does not establish physical truth, authority, safety, or permission.

## Input -> Runtime -> Output

| Stage | Execution record |
|---|---|
| INPUT | {"parsed_records":0,"sources":0} |
| INGEST | {"evidence_sources":2,"warnings":0} |
| REPRESENT | {"nodes":15,"unresolved_numeric_meanings":0} |
| PAIR | {"candidates":0,"deferred":0,"selected_pairs":9} |
| EVALUATE | {"evaluated_pairs":9,"status":"CONFLICT"} |
| AGGREGATE | {"codec_audits":1,"groups":3} |
| OUTPUT | {"automatic_actions":0,"review_findings":7} |

## Pair results

| Pair | Status | Delta | Raw /100 | Supported /100 |
|---|---|---|---|---|
| confidence-overclaim | CONFLICT | not scalar | 100.0 | 90.0 |
| coverage-overclaim | CONFLICT | -40 % | 100.0 | 98.0 |
| dependence-overclaim | CONFLICT | -1 count | 100.0 | 100.0 |
| freshness-claim | CONFLICT | not scalar | 100.0 | 100.0 |
| qualified-coverage | ALIGNED | not scalar | 0.0 | 0.0 |
| support-case-count | ALIGNED | 0 count | 0.0 | 0.0 |
| uncertain-count | PARTIAL | not scalar | unknown | unknown |
| unsupported-absence | NOT\_COMPARABLE | not evaluated | unknown | unknown |
| zero-preserved | ALIGNED | 0 count | 0.0 | 0.0 |

## Review findings
- **REVIEW\_DISCREPANCY**: Comparable representations have disjoint admissible values; inspect both sources.
- **REVIEW\_DISCREPANCY**: Comparable representations have disjoint admissible values; inspect both sources.
- **REVIEW\_DISCREPANCY**: Comparable representations have disjoint admissible values; inspect both sources.
- **REVIEW\_DISCREPANCY**: Comparable representations have disjoint admissible values; inspect both sources.
- **RESOLVE\_OVERLAP**: The observation allows both satisfying and nonsatisfying cases; obtain tighter evidence.
- **REPAIR\_PAIRING**: Revise the pairing contract or provide a justified inference bridge; do not call this numerical agreement.
- **REVIEW\_TRANSFORMATION**: Material meaning, scope, uncertainty or support was not shown to be preserved.

## Boundaries
- NOT_COMPARABLE is not CONFLICT. Missing numeric support is not zero risk.
- Unpaired nodes have no collision score. Coverage concerns declared material, not every semantic fact in the original.
- Auto pairing is an explicit exact-metadata policy, not unrestricted semantic understanding.
- Optional origin/retreat context is attributed narrative and is not scored.

Job fingerprint: `b94876c006e4cb8a08986bf8775993c44cfe42a17af74485e0dc597b8e66ca66`. Content identity only; not a signature.
