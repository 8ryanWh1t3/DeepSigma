# 20 — DLR: Claim-Native Refactor

> **Schema**: [`specs/dlr.schema.json`](../specs/dlr.schema.json)
> > **Example**: [`llm_data_model/03_examples/dlr_claim_native_example.json`](../llm_data_model/03_examples/dlr_claim_native_example.json)
> > > **Depends on**: [19 — Claim Primitive](19-claim-primitive.md)
> > > > **Version**: 1.0.0
> > > > > **Status**: Active
> > > > >
> > > > > ---
> > > > >
> > > > > ## What changed
> > > > >
> > > > > The original DLR (`coherence_ops/dlr.py`) was episode-centric: it extracted flat metadata from a sealed DecisionEpisode (DTE ref, action contract fields, verification result, policy stamp, outcome code). It had no concept of claims, no rationale graph, and no freshness tracking.
> > > > >
> > > > > The claim-native DLR (`specs/dlr.schema.json`) is **claim-centric**: a DLR is now a categorised list of claim references forming a rationale graph, plus the policy/action/verification/outcome metadata from the episode that produced them.
> > > > >
> > > > > ---
> > > > >
> > > > > ## Core idea
> > > > >
> > > > > A DLR answers three questions:
> > > > >
> > > > > 1. **What claims governed this decision?** (the `claims` object)
> > > > > 2. 2. **How did those claims relate to each other?** (the `rationaleGraph`)
> > > > >    3. 3. **Was the policy followed and were the claims fresh?** (the `policyStamp` + `freshnessSnapshot`)
> > > > >      
> > > > >       4. ---
> > > > >      
> > > > >       5. ## The claims object
> > > > >      
> > > > >       6. Claims are categorised into five decision stages:
> > > > >
> > > > > | Stage | What goes here | Typical truthTypes |
> > > > > |---|---|---|
> > > > > | `context` | Situational awareness claims that triggered or framed the decision | observation, inference |
> > > > > | `rationale` | Reasoning claims — the "why" behind the chosen path | inference, assumption, forecast |
> > > > > | `action` | Policy/norm/constraint claims that justified the action | norm, constraint |
> > > > > | `verification` | Post-action observations confirming or denying the result | observation |
> > > > > | `outcome` | Final state claims summarising what actually happened | observation |
> > > > >
> > > > > Each claim reference is a `claimRef` — not just a bare claimId, but a **decision-time snapshot**:
> > > > >
> > > > > | Field | Purpose |
> > > > > |---|---|
> > > > > | `claimId` | Reference to the Claim primitive |
> > > > > | `truthType` | Snapshot of the claim's epistemic type at decision time |
> > > > > | `confidenceAtDecision` | Snapshot of confidence score at decision time |
> > > > > | `statusLightAtDecision` | Snapshot of traffic light at decision time |
> > > > > | `wasFresh` | Whether the claim was within its halfLife |
> > > > > | `role` | Role this claim played (trigger, baseline, constraint, etc.) |
> > > > >
> > > > > This means you can audit a decision **after the fact** even if the underlying claims have since been superseded, expired, or patched.
> > > > >
> > > > > ---
> > > > >
> > > > > ## The rationale graph
> > > > >
> > > > > The `rationaleGraph` is a directed graph with typed, weighted edges between claims:
> > > > >
> > > > > | Edge type | Meaning |
> > > > > |---|---|
> > > > > | `depends_on` | Upstream dependency |
> > > > > | `supports` | Corroborating evidence |
> > > > > | `contradicts` | Active conflict (should trigger review) |
> > > > > | `supersedes` | Replaced a prior claim |
> > > > > | `informs` | Provides input to reasoning |
> > > > > | `justifies` | Provides policy/norm basis for action |
> > > > > | `verifies` | Post-action confirmation |
> > > > >
> > > > > The `rootClaims` array identifies the entry-point claims that initiated the decision.
> > > > >
> > > > > Edge weights carry the source claim's confidence, enabling confidence propagation analysis: if a root claim's confidence drops, you can trace the impact through the graph.
> > > > >
> > > > > ---
> > > > >
> > > > > ## Freshness snapshot
> > > > >
> > > > > The `freshnessSnapshot` captures the freshness state of all claims at decision time:
> > > > >
> > > > > | Field | Purpose |
> > > > > |---|---|
> > > > > | `allClaimsFresh` | Boolean: were all claims within halfLife? |
> > > > > | `expiredClaims` | List of claimIds past their halfLife |
> > > > > | `stalestClaimAge` | Human-readable age of the oldest claim |
> > > > >
> > > > > This is critical for audit: if a decision was made on stale claims, the DLR records that fact permanently.
> > > > >
> > > > > ---
> > > > >
> > > > > ## Migration from episode-centric DLR
> > > > >
> > > > > The existing `coherence_ops/dlr.py` `DLREntry` dataclass maps to the claim-native DLR as follows:
> > > > >
> > > > > | Old DLREntry field | New DLR field |
> > > > > |---|---|
> > > > > | `dlr_id` | `dlrId` (same derivation, new format: DLR-prefix) |
> > > > > | `episode_id` | `episodeId` |
> > > > > | `decision_type` | `decisionType` |
> > > > > | `recorded_at` | `recordedAt` |
> > > > > | `dte_ref` | `dteRef` (same structure) |
> > > > > | `action_contract` | `actionSummary` (restructured) |
> > > > > | `verification` | `verificationResult` (restructured) |
> > > > > | `policy_stamp` | `policyStamp` (expanded with result enum) |
> > > > > | `outcome_code` | `outcome.code` (expanded with reason) |
> > > > > | `degrade_step` | `degradeStep` |
> > > > > | `tags` | `tags` |
> > > > > | *(missing)* | `claims` (new — the core of claim-native DLR) |
> > > > > | *(missing)* | `rationaleGraph` (new — claim dependency graph) |
> > > > > | *(missing)* | `freshnessSnapshot` (new — claim freshness at decision time) |
> > > > > | *(missing)* | `coherenceScore` (new — score at DLR creation) |
> > > > > | *(missing)* | `seal` (new — immutable seal for the DLR itself) |
> > > > >
> > > > > The `DLRBuilder.from_episode()` method can be extended to accept a `claims` parameter (a list of Claim primitives referenced by the episode) and build the `claims` categorisation + `rationaleGraph` from claim graph edges.
> > > > >
> > > > > ---
> > > > >
> > > > > ## Downstream impact
> > > > >
> > > > > | Consumer | Impact |
> > > > > |---|---|
> > > > > | **CoherenceScorer** (`scoring.py`) | `_score_policy_adherence()` can now check `freshnessSnapshot.allClaimsFresh` in addition to policy stamp presence. Claim-level confidence gives richer scoring. |
> > > > > | **MemoryGraph** (`mg.py`) | Can add `CLAIM` as a new `NodeKind` and create edges from claims to episodes, enabling claim-level provenance queries. |
> > > > > | **IRISEngine** (`iris.py`) | WHY queries can now walk the `rationaleGraph` directly instead of relying on episode-level evidence refs. |
> > > > > | **ReflectionSession** (`rs.py`) | Can aggregate claim confidence distributions across episodes, not just outcome codes. |
> > > > > | **DriftSignalCollector** (`ds.py`) | Can detect claim-level drift (confidence decay, half-life expiry) in addition to episode-level drift. |
> > > > >
> > > > > ---
> > > > >
> > > > > ## Files
> > > > >
> > > > > | File | Path |
> > > > > |---|---|
> > > > > | JSON Schema | `specs/dlr.schema.json` |
> > > > > | Worked Example | `llm_data_model/03_examples/dlr_claim_native_example.json` |
> > > > > | This Document | `docs/20-dlr-claim-native.md` |
> > > > > | Original DLR (preserved) | `coherence_ops/dlr.py` |
> > > > >
> > > > > ---
> > > > >
> > > > > ## What comes next
> > > > >
> > > > > With both Claim (A) and DLR (B) as claim-native schemas:
> > > > >
> > > > > - **Canon** becomes: promote a set of claimIds from DLR to long-term blessed memory
> > > > > - - **Drift** becomes: detect when claims referenced by DLRs expire, get contradicted, or lose confidence
> > > > >   - - **Retcon** becomes: supersede claims in a DLR and create a new DLR version with updated rationale graph
> > > > >     - - **IRIS** becomes: walk the rationale graph to answer WHY/WHAT_CHANGED/WHAT_DRIFTED with full provenance
