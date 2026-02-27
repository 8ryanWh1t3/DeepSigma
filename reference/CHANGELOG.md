# Constitution Changelog

All contract surface changes are logged here with compatibility annotations.

## v2.0.8 — Scalability Evidence + SSI Recovery

`COMPATIBLE:` Promote re-encrypt benchmark to CI-eligible evidence, add scalability regression gate, benchmark trend visualization. Scalability KPI 5.38 → 10.0 via real benchmark infrastructure. SSI trajectory improving: 37.71 → 39.05. No schema changes.

### Migration

**Affected schemas**: None
**Consumer action**: None — no schema changes in this release.
**Rollback**: Yes — all changes are additive tooling and evidence.

---

## v2.0.7 — Nonlinear Stability + Credibility Hardening

`COMPATIBLE:` Add stale artifact kill-switch, TEC sensitivity analysis, security proof pack v2, banded radar rendering, and KPI eligibility tier validation. No schema changes. Policy version aligned to GOV-2.0.7.

### Migration

**Affected schemas**: None
**Consumer action**: None — no schema changes in this release.
**Rollback**: Yes — all changes are additive governance tooling.
**Fingerprint**: `sha256:6a0c479e7a0fcaeb`

---

## v2.0.6-a — Compat Rules + Contract Fingerprint

`ADDITIVE:` Add `contractFingerprint` to FEEDS envelope schema and credibility packets. Add `COMPAT_RULES.md` defining MAJOR/MINOR/PATCH break classification. Contract fingerprint is a single SHA-256 digest of the schema manifest, embedded in every emitted artifact for tamper-evident provenance.

### Migration

**Affected schemas**: `feeds_event_envelope.schema.json`
**Consumer action**: None — new field is optional. Consumers may read `contractFingerprint` for provenance verification.
**Rollback**: Yes — old consumers ignore the new optional field.
**Fingerprint**: `sha256:6a0c479e7a0fcaeb`

---

## v2.0.6 — Constitution Established

`COMPATIBLE:` Initial constitution lock. 26 schemas fingerprinted. Policy version aligned to GOV-2.0.6. Schema manifest generated. Constitution gate enforced in CI.

Schemas locked:

- `claim.schema.json`, `dlr.schema.json`, `episode.schema.json`, `canon.schema.json`
- `drift.schema.json`, `dte.schema.json`, `action_contract.schema.json`
- `coherence_manifest.schema.json`, `coherence_report.schema.json`
- `iris_query.schema.json`, `prime_gate.schema.json`, `retcon.schema.json`
- `connector_envelope.schema.json`, `crypto_envelope.schema.json`
- `exhaust.schema.json`, `decision_episode_chain.schema.json`
- `security_crypto_policy.schema.json`, `security_event.schema.json`
- `authority_ledger.schema.json`
- FEEDS: `feeds_event_envelope.schema.json`, `decision_lineage.schema.json`, `canon_entry.schema.json`, `authority_slice.schema.json`, `truth_snapshot.schema.json`, `packet_index.schema.json`, `drift_signal.schema.json`
