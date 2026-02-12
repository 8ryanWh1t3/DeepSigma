# Query Patterns

The top 20 queries the LLM Data Model must support.  Each pattern shows the retrieval method (vector, keyword, graph, or hybrid) and the key filters.

## Agent queries (runtime)

| # | Pattern | Method | Description |
|---|---|---|---|
| 1 | **Context assembly** | Hybrid | Given a decision type, retrieve all fresh Claims and Entities relevant to the decision context.  Vector search on decision description + keyword filter on domain + freshness gate. |
| 2 | **Evidence lookup** | Graph | Given a Claim record_id, traverse `derived_from` and `supports` edges to find all supporting evidence records. |
| 3 | **Entity snapshot** | Keyword | Given an entity_id, retrieve the latest Entity record (by `observed_at`) that is not expired. |
| 4 | **Policy lookup** | Keyword | Given a decision_type, retrieve the active Document record with matching DTE definition.  Filter: `record_type=Document`, `content.decision_type=X`, `ttl=0`, latest version. |
| 5 | **Similar decisions** | Vector | Given the current context, find the 5 most similar past DecisionEpisodes.  Vector search on context description + filter `record_type=DecisionEpisode`. |

## Supervisor queries (validation)

| # | Pattern | Method | Description |
|---|---|---|---|
| 6 | **Freshness check** | Keyword | For a set of record_ids, verify that `observed_at + ttl > now()` for all of them.  Returns stale records. |
| 7 | **Contradiction scan** | Graph | Given a Claim, find all records connected by `contradicts` edges.  If any exist, flag for human review. |
| 8 | **Provenance depth** | Graph | Given a record_id, count the depth of the provenance chain by traversing `derived_from` edges.  Minimum depth for high-stakes decisions: 3. |
| 9 | **Seal verification** | Keyword | Retrieve all records modified in the last hour and verify `seal.hash` matches recomputed hash. |
| 10 | **TTL breach scan** | Keyword | Find all records where `observed_at + ttl < now()` and `record_type = Claim`.  These are expired claims still in active indexes. |

## Auditor queries (governance)

| # | Pattern | Method | Description |
|---|---|---|---|
| 11 | **Decision trace** | Graph | Given a DecisionEpisode record_id, traverse all `derived_from`, `supports`, and `caused_by` edges to build the full evidence tree.  Max depth: 10. |
| 12 | **Actor history** | Keyword | Given an actor_id, retrieve all records where `source.actor.id = X`, ordered by `created_at` descending.  Paginated. |
| 13 | **Drift timeline** | Keyword + time range | Retrieve all Event records with `labels.domain = "drift"` in a given time window.  Group by `content.drift_type`. |
| 14 | **Policy version history** | Graph | Given a Document (policy) record_id, follow `supersedes` chain backward to build the complete version history. |
| 15 | **Confidence distribution** | Keyword + aggregation | For a given domain, compute the distribution of `confidence.score` across all active (non-expired) Claims.  Histogram buckets: 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0. |

## Drift detector queries (monitoring)

| # | Pattern | Method | Description |
|---|---|---|---|
| 16 | **Recent episodes** | Keyword + time range | Retrieve the last N DecisionEpisodes for a given decision_type.  Used by DS to detect drift trends. |
| 17 | **Fallback frequency** | Keyword + aggregation | Count episodes where `content.telemetry.fallback_used = true` in the last hour, grouped by `content.decision_type`. |
| 18 | **Outcome distribution** | Keyword + aggregation | For a given decision_type in the last 24h, count episodes by `content.outcome.code` (success/partial/fail/abstain/bypassed). |

## Coherence Ops queries (scoring)

| # | Pattern | Method | Description |
|---|---|---|---|
| 19 | **Link integrity check** | Graph | For all records ingested in the last hour, verify that every `links[].target` resolves to an existing record.  Broken links reduce the consistency score. |
| 20 | **Completeness audit** | Keyword + aggregation | Count records missing optional-but-recommended fields (`assumption_half_life`, `labels.sensitivity`, `labels.project`).  Report completion percentage by domain. |
