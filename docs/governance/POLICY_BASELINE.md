# Governance Policy Baseline

**Version:** GOV-2.0.4
**Effective:** 2026-02-23

---

## Core Principles

1. **Seal → Version → Patch.** Once sealed, artifacts are immutable. Corrections create patches.
2. **Authority is bound.** Every action requires a named actor, a defined role, and an explicit scope.
3. **Refusal is structural.** The system must be able to refuse unauthorized actions and emit a refusal artifact.
4. **Enforcement is emitted.** Gate checks produce admissible artifacts, not silent pass/fail.
5. **Replay without live access.** Any sealed run must be reconstructable from exported artifacts alone.

## Decision Authority

- Decisions require an operator with `direct` or `delegated` authority.
- Authority must have an `effective_at` timestamp and may have an `expires_at`.
- Expired authority cannot seal new artifacts.

## Scope Binding

- Every sealed run binds to an explicit scope: decisions, claims, patches, prompts, datasets.
- Actions outside bound scope trigger `SCOPE_VIOLATION` refusal.

## Policy Versioning

- This document is hashed (SHA-256) and embedded in every sealed run.
- Policy version string is read from `POLICY_VERSION.txt`.
- If policy changes, the version must be incremented and the hash will change.

## Refusal Codes

| Code | Meaning | Severity |
|------|---------|----------|
| `NO_AUTHORITY` | Actor lacks authority for requested scope | BLOCK |
| `SCOPE_VIOLATION` | Action outside bound scope | BLOCK |
| `POLICY_EXPIRED` | Governing policy version expired | BLOCK |
| `INSUFFICIENT_EVIDENCE` | Below evidence threshold | WARN |
| `UNSAFE_ACTION` | Classified as unsafe under policy | BLOCK |
| `MISSING_PROVENANCE` | Provenance fields absent | BLOCK |

## Retention

- Sealed runs are retained indefinitely.
- Manifests are retained alongside sealed runs.
- Telemetry events are retained for 1 year minimum.
