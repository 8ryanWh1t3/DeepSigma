# Core concepts

## DTE (Decision Timing Envelope)
A per-decision contract:
- deadline (decision window)
- stage budgets (context/plan/act/verify)
- freshness TTL gates
- limits (hops/fan-out/tool calls/chain depth)
- degrade ladder
- safety + verification thresholds

## Safe Action Contract
A required envelope for state-changing actions:
- blast radius tier
- idempotency key
- rollback plan (above thresholds)
- authorization mode (auto/hitl/blocked)

## DecisionEpisode
The sealed unit of audit:
truth used → reasoning → action → verification → outcome

## DriftEvent
Structured failure modes:
time, freshness, fallback, bypass, verify, outcome, fanout, contention
