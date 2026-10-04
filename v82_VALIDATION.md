# Deep Sigma / VINCULUM pyLib v0.8.2 — Candidate Validation

**Status:** CANDIDATE — not locked  
**Date:** 2026-10-04  
**Negative baseline:** v0.8.0 ZIP SHA-256 `5ccdf80ac06e5fc9dc8a0374757add23a9e11d4bcfbd082a9d5d96f93d982902`

## Release purpose

v0.8.2 absorbs the v0.8.1 hardening backlog and adds bounded containment/anchor capability without reopening the proven VINCULUM cross-order or Navigable Fold semantics. The governing boundary is:

> Models may propose, patch and review. Consequential Apply requires attributable human authority. Apply is not closure; post-Apply observation and a lesson record are required before CLOSED.

## Exact wheel

- `dist/vinculum_pylib-0.8.2-py3-none-any.whl`
- SHA-256: `af8ee9b25bf6f4be276c00a851ef4cc70e601cbd1eacdac5d6e2d403e0449910`
- Python source files compared between `src/` and the wheel: **101**
- Source↔wheel differences: **0**

## Test results

| Gate | Result |
|---|---:|
| Source suite | **485 passed, 0 failed, 1 skipped** |
| Installed-wheel suite, no adjacent `src/` | **485 passed, 0 failed, 1 skipped** |
| Claude-successor acceptance probes | **28 PASS, 0 FAIL, 1 HOLD, 1 SKIP** |
| v0.8.2 authority/containment gates | **10/10 PASS** |
| v0.8.0 negative baseline | **9 PASS, 17 FAIL, 3 HOLD, 1 SKIP** |

The single pytest skip is the optional PyArrow/Parquet path, unavailable in this build environment.

### Claude-successor HOLD

`H3` remains **HOLD**, not PASS: when `auditor_model` is not configured, the generating model may also perform the review. This no longer grants authority: a passing review ends at `READY_FOR_AUTHORITY`, not Apply. Independent review remains a deployment/policy decision.

### Intentional SKIP

`H4` is **SKIP** because `deepsigma==2.1.3` is deliberately excluded from this candidate. The legacy Phase I bridge is not treated as release evidence for v0.8.2.

## 0.8.0 → 0.8.2 closure evidence

The exact v0.8.0 baseline reproduces Claude's blockers: **17 FAIL**. The v0.8.2 successor probes against the exact installed candidate wheel produce **0 FAIL**. Both result sets are retained under `validation/`.

## Authority / fail-closed closure

The following are executable v0.8.2 release gates and all pass:

1. **A1_NO_AUTO_APPLY** — no model path auto-applies.
2. **A2_IMMUTABLE_ROSTER** — runtime cannot mutate the trusted approver roster.
3. **A3_ATTRIBUTED_DECISION** — human decisions carry actor/authority evidence and are ledgered.
4. **A4_APPLY_NOT_CLOSURE** — Apply requires a later observation and lesson before CLOSED.
5. **A5_EXTERNAL_ANCHOR** — ledger tips can be retained/verified externally.
6. **A6_LEDGER_CONCURRENCY** — concurrent appends retain a valid chain.
7. **A7_ENDPOINT_CONTAINMENT** — model URLs are HTTPS or loopback HTTP; unsafe schemes/remote cleartext are rejected.
8. **A8_JIT_NO_COMPOSITE** — JIT remains four independent lenses; no readiness composite.
9. **A9_OBJECT_NO_COMPOSITES** — banned per-object/global composite outputs are absent.
10. **A10_NO_WEIGHTED_MEAN** — cross-pair weighted mean collision is absent.

## Semantic preservation

v0.8.2 intentionally preserves the cross-order pairwise comparison model and the full Navigable Fold. The score cleanup removes universal/object composites and public decision surfaces; it does **not** reinterpret valid pairwise range, conflict, coverage, P/D channel, or hinge diagnostics as truth or authority.

## Product boundaries

- **PATHFINDER, RESONATOR and COMPOSER** are interface/integration stubs in this wheel, not claims of those products being implemented here.
- The former `vinculum-lattice`/`LatticeDB` naming is retired in favor of **VINCULUM Graph**.
- C-UAS scenario material and the DoD autonomy profile are not current wheel capabilities.
- `NOTICE` is a rights notice; it is not an open-source license grant.
- `MANIFEST.json` / `MANIFEST.sha256` are hash lists, not signatures or trust anchors.

## v0.8.2 additions beyond hardening

- host-facing `ContainmentPolicy` for model endpoint and payload bounds;
- external ledger-anchor helpers;
- neutral VINCULUM Graph surface;
- post-Apply observation + lesson closure;
- canonical Coherence Loop retained separately from the mission autonomy loop.

## Explicit non-claims

This candidate does not claim:

- truth, risk, readiness or authorization from a score;
- operational certification;
- production IAM or real-world identity authentication;
- OS-level sandboxing;
- live third-party platform integration;
- automatic command action;
- outcome success merely because Apply occurred.

## Release disposition

This artifact is suitable for **external evaluation / lock review**. It is **not yet locked**. A lock should bind to the final ZIP SHA-256 after the hash-list inventory and final ZIP verification are complete.
