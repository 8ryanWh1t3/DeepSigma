# Ambiguity Policy (Default Deny)

If any of the following are true, execution MUST HALT:

1) Missing or expired intent TTL
2) Missing authority signature or unverifiable signature
3) Missing provenance for required inputs
4) Conflicting authority claims (two different signers for same action)
5) Claim->Evidence binding incomplete
6) Hash mismatch anywhere in the chain
7) Unknown policy decision (cannot evaluate)

Ambiguity is treated as risk. Default posture: DENY.
