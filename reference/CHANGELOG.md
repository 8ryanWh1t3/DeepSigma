# Constitution Changelog

All contract surface changes are logged here with compatibility annotations.

## v2.0.13 — DISR Closure

`COMPATIBLE:` Authority ledger verify_chain() and detect_replay() (#327), audit summary export mode for export_authority_ledger.py (#326 streaming re-encrypt checkpoint already complete), DISR provider abstraction confirmed with 5 providers (#324). DISR architecture epic #313 closed. SSI stability release — zero KPI movement.

### Migration

**Affected schemas**: None
**Consumer action**: None — no schema changes in this release.
**Rollback**: Yes — additive methods + tests only.

---

## v2.0.12 — Schema + Determinism

`COMPATIBLE:` Schema version enforcement self-check wired into CI (#417), input snapshot fingerprint CI validation (#416), replay reproducibility tests promoted to required enterprise CI check (#418). Technical completeness epic #400 closed. Reconstruct replay workflow expanded with PR trigger. SSI stability release — zero KPI movement.

### Migration

**Affected schemas**: None
**Consumer action**: None — no schema changes in this release.
**Rollback**: Yes — CI wiring + test expansion only.

---

## v2.0.11 — Enterprise Hardening

`COMPATIBLE:` Fix Helm chart appVersion alignment (#407), audit-neutral pack CI validation (#408), operator runbook enterprise release checklist + release readiness gate (#409). Enterprise readiness epic #397 closed. Helm lint, audit-pack self-check, and release-check self-check wired into CI. SSI stability release — zero KPI movement.

### Migration

**Affected schemas**: None
**Consumer action**: None — no schema changes in this release.
**Rollback**: Yes — CI wiring + docs only.

---

## v2.0.10 — Automation Closure

`COMPATIBLE:` Wire pre-execution gate (#401), idempotency guard (#402), and replay validation (#403) into CI determinism gate. All three scripts pass `--self-check`. Automation depth epic #395 closed. SSI stability release — zero KPI movement.

### Migration

**Affected schemas**: None
**Consumer action**: None — no schema changes in this release.
**Rollback**: Yes — CI wiring only.

---

## v2.0.9 — Authority + Economic Evidence

`COMPATIBLE:` Production signature key custody + verification (#413), structural refusal authority contract (#414), authority evidence chain export (#415). P0 #325 closed — authority cap lifted 6.0 → 7.0. Decision cost ledger + economic_metrics.json (#404, #405), economic KPI ingestion gate (#406) — dedicated evidence path uncaps economic measurability 4.88 → 10.0. All 8 KPIs now >= 7.0.

### Migration

**Affected schemas**: None
**Consumer action**: None — no schema changes in this release.
**Rollback**: Yes — all changes are additive evidence and tooling.

---

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
