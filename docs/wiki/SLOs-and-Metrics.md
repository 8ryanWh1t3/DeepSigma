# SLOs & Metrics

Recommended SLOs:
- P99 end-to-end ≤ decisionWindowMs
- freshness compliance ≥ 99% (TTL/TOCTOU)
- verifier pass rate ≥ target
- drift recurrence trending down
- median “why retrieval” ≤ 60s (via MG)

Export via OpenTelemetry where possible.
