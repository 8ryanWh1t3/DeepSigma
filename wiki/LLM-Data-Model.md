# LLM Data Model

To support RAL, your data must be agent-safe:
- `capturedAt` timestamps
- TTL / maxFeatureAge fields
- provenance (`sourceRef` / evidence refs)
- action contracts are first-class objects
- episodes + drift are first-class entities

See repo doc: `docs/10-coherence-ops-integration.md`
