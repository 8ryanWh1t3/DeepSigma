# Security

Threats RAL is designed to mitigate:
- stale context (TOCTOU)
- unsafe tool actions (missing idempotency/rollback)
- prompt/tool injection (reduce blast radius with allowlists + HITL)
- uncontrolled fanout and retry storms

Recommended:
- tool allowlists per blast radius tier
- signed policy packs (future)
- strict auth modes for high blast radius actions
