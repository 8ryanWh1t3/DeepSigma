# Palantir Foundry

Foundry remains Foundry; RAL governs calls into it.

Patterns:
- feature fetch wrapper returns `{value, capturedAt, sourceRef}`
- action adapter requires Safe Action Contract
- verifier reads authoritative ontology state after write
