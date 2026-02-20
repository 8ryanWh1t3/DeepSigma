# Runtime Flow

```text
1) submit_task(decisionType)  → loads DTE + policy pack rules
2) tool_execute(...)          → returns {result, capturedAt, sourceRef}
3) TTL/TOCTOU gate            → stale? degrade/abstain
4) action_dispatch(contract)  → enforce idempotency/rollback/auth
5) verify_run(method)         → postconditions
6) episode_seal               → hash + seal DecisionEpisode
7) drift_emit (if needed)     → typed drift + fingerprint → patch workflow
```

Key idea:
**Policy Pack → Degrade Ladder → Verification → Seal → Drift**
