# Deep Sigma Zipf pilot contract 1.0

This is an executable synthetic pilot, not a production authorization system. Uploaded source origins, evidence assessments, identities and approvals are scenario assertions. The tool does not authenticate reviewers or establish real-world truth. No LLM or network service is used. A score never establishes verification.

## Input

JSON object with required keys `schema_version` (exact `1.0`), `as_of` (UTC timestamp YYYY-MM-DDTHH:MM:SSZ), `review_budget` (integer 1..100), `policy`, `aliases` (alias-to-canonical concept string map), `claims` (1..1000), `reports` (0..50000). Optional `labels` is evaluator ground truth and MUST NOT influence ranking or gates.

Policy required fields: `id` (nonempty string), `version` (positive integer), `rarity_cap` (integer 0..30), `min_relevance` and `min_quality` (integers 0..100), `min_independent_support` (integer 1..10), `required_evidence_types` (nonempty unique string array), `max_evidence_age_days` (integer 1..3650), `reviewer_roles` and `authority_roles` (nonempty unique string arrays), `intended_use` (nonempty string).

Each claim requires: `id` (unique identifier), `version` (positive integer), `concept`, `statement`, integer `relevance`, `consequence`, `quality` (0..100); boolean `contradiction` and `mandatory`; `required_evidence_types` (unique string array, may be empty because policy minimum still applies); `evidence` (array); `review` (object or null); `authority` (object or null).

Evidence requires `id`, `origin_id`, `event_id`, `kind`, `stance` (`supports`, `contradicts`, `neutral`), `claim_version`, `observed_at` (UTC timestamp), and boolean `support_assessed`. Source origins represent declared independent origins; multiple report IDs or multiple LLM outputs do not prove independence. Evidence IDs must be unique within a claim. Supporting evidence is usable only when assessed, version-matched, not future-dated and within policy age. A current usable contradiction yields HOLD regardless of frequency. Preserve unassessed contradictory evidence as a review reason rather than silently ignoring it.

Review, when supplied, requires `reviewer_id`, `role`, `claim_version`, `policy_version`, `decision` (`approved` or `rejected`), `expires_at` (UTC timestamp). Authority requires `authority_id`, `role`, `claim_version`, `policy_version`, `intended_use`, `expires_at`, boolean `revoked`. Review and authority are bound to their containing exact claim by containment and claim_version. All valid states also require current policy version. Expiry equal to as_of is expired.

Each report requires unique `id`, known `claim_id`, `origin_id`, `event_id`. Reports may duplicate the same originating event. Reject reuse of an (origin_id,event_id) pair across different claims across reports and evidence; copies for one claim are allowed. This simplified event model uses claim-specific event IDs; a future multi-claim event model must explicitly represent shared observations. Evidence events sharing origin/event identity must not conflict in their kind, stance, version, observation time or assessment within a claim. Identity strings use ASCII letters/digits plus `_ . : -`, 1..80 characters. Concepts and alias keys/values are 1..80 ASCII letters/digits, spaces, underscores or hyphens, normalized by trimming, lowercase and collapsing spaces. Alias resolution permits one hop only; reject cycles, self-maps or chained mappings. Reject duplicate normalized alias keys. Statements may contain Unicode but are 1..2000 characters. Limit review/authority role and use strings to 80 characters. Reject malformed inputs rather than silently treating missing required values as valid. Reject booleans as integers and nonfinite numbers. Mathematical integer JSON values such as 5.0 are allowed; version values must be no larger than JavaScript's safe integer maximum 9007199254740991. Unknown optional labels are not used by core evaluation.

## Ranking

Collapse reports by (origin_id,event_id), retaining raw report counts. Evidence does not create report observations implicitly. Group those unique events by normalized canonical concept. `N` = total unique report events and `df` = events for the claim's canonical concept. Genuine recurrence remains in counts. Duplicate copies cannot change either score.

`base_score = floor((45*relevance + 35*consequence + 20*quality)/100)`.

Illustrative frequency-sensitive baseline for a claim with at least one report event: `base_score + min(20, 4*floor(log2(1+df)))`. A claim with no report events receives only base_score even if other claims share its concept. This is an explicit synthetic comparator, not a claim about any deployed model.

Compensated score: `base_score + rarity_bonus`; bonus is zero unless the claim has at least one report event, relevance and quality meet policy thresholds, df >= 1, and N > 1. Otherwise `rarity_bonus = floor(rarity_cap*(N-df)/(N-1))`. For N=0 or N=1 bonus is zero. This bounded inverse-frequency heuristic does not assert a fitted Zipf distribution or measure truth.

Sort each ranking by score descending, consequence descending, then ASCII claim ID ascending. All mandatory claims are in a separate lane and always included; `review_budget` applies ONLY to nonmandatory claims. A claim with no report still remains a candidate on base score, without rarity bonus. It can also remain mandatory.

## Gate

Evaluate every claim independently of attention score. Gate status is `ELIGIBLE` or `HOLD`, always `simulated: true`. ELIGIBLE means only that the supplied scenario metadata passes policy. Require assessed, current, version-matched supporting evidence from at least policy.min_independent_support distinct origin IDs and coverage of the union of policy+claim evidence types by that same usable supporting set. Count each origin once. Hold on contradiction flag or any current, version-matched contradictory evidence (assessed or unassessed). Hold on absent, expired, rejected, wrong-role, mismatched-version review; absent, expired, revoked, wrong-role, mismatched-version or wrong-use authority. Exclude stale/unassessed/future/version-mismatched support and explain exclusion. Missing support, gaps, review and authority are fail-closed. The local demo does not publish, approve, or enforce a downstream production action.

## Output

Top-level `schema_version`, `as_of`, `policy` (`id`, `version`), `items`, `modes`, `diagnostics`.

Each item: `id`, `statement`, `canonical_concept`, `mandatory`, `relevance`, `consequence`, `quality`, `base_score`, `baseline_score`, `rarity_bonus`, `compensated_score`, `report_count`, `independent_events`, `concept_events`, `reasons` (array of explanatory strings), `gate`.

Gate: `status`, `simulated`, `reasons` (array of stable reason codes), `independent_support_origins` (sorted ID array), `missing_evidence_types` (sorted string array), `excluded_evidence` (array of objects with `id`, `reason`). Gate reason codes: `CONTRADICTION`, `INSUFFICIENT_INDEPENDENT_SUPPORT`, `MISSING_EVIDENCE_TYPES`, `MISSING_REVIEW`, `REVIEW_EXPIRED`, `REVIEW_REJECTED`, `REVIEW_ROLE`, `REVIEW_VERSION`, `MISSING_AUTHORITY`, `AUTHORITY_EXPIRED`, `AUTHORITY_REVOKED`, `AUTHORITY_ROLE`, `AUTHORITY_VERSION`, `AUTHORITY_USE`. Excluded evidence reason priority: VERSION_MISMATCH, FUTURE_EVIDENCE, STALE_EVIDENCE, UNASSESSED_SUPPORT; non-support entries not in usable set are not exclusions unless date/version invalid. Deduplicate reasons and preserve defined order.

Modes `baseline`, `compensated`, `full_control` each contain `mandatory_ids` (ASCII sorted), `review_ids` (ranked), `selected_ids` (mandatory then review), `gate_applied` (false,false,true). full_control has same selection as compensated; its gate outcome is diagnostic simulation and never production authorization. All items expose gate results so the UI can explain them in any mode.

Diagnostics: `report_count`, `unique_events`, `duplicate_reports`, `claims`, `mandatory_count`, `review_budget`. Output items sorted by ASCII ID. No clock reads in core evaluation; as_of is explicit.

## Interfaces

Python: `from deep_sigma_zipf.engine import evaluate, ValidationError`; `evaluate(payload)` returns output or raises ValidationError.

JavaScript: web/engine.js exposes `globalThis.DeepSigmaZipf.evaluate(payload)` and CommonJS `module.exports = {evaluate, ValidationError}`. Function is synchronous, no DOM or network. Port Python behavior for parity.

Browser: web/index.html loads engine.js, demo.js (`globalThis.DEEP_SIGMA_DEMO`), app.js using classic scripts, works from file://. In HTTP mode POST /api/evaluate JSON body to local Python evaluator; GET /api/demo returns default payload; GET /api/health. Display local simulation status explicitly in both modes. Python server binds only 127.0.0.1. Reports/claims and all imported strings rendered using textContent, never untrusted innerHTML. The web UI may read evaluator labels for separate metrics only.
