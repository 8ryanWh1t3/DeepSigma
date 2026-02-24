# DLR-2026-001

## 🧭 Intent
Intent: Maintain coherent response posture for fictional threat-intel ingestion pipeline.

## 🔍 Context
Context: The team observed increased false positives from an upstream fictional telemetry source and needed a rapid, reversible decision.

## 🧾 Decision
Decision: Keep ingestion enabled with tighter filtering and explicit expiry on assumptions.

## 🧪 Options Considered
- Option 1: Disable source entirely.
- Option 2: Keep source with stricter thresholding and active review cadence.

### Rejected + Why
- Rejected option: Disable source entirely.
  - Why rejected: Would remove useful signal and degrade response coverage.

## 🧱 Assumptions
- Assumption ID: A-2026-001
  - Statement: Upstream source false positive rate remains below 12%.
  - TTL: 14 days
  - Expiry date (YYYY-MM-DD): 2026-02-10
- Assumption ID: A-2026-002
  - Statement: Human review queue can process daily signal volume within 4 hours.
  - TTL: 14 days
  - Expiry date (YYYY-MM-DD): 2026-03-05

## 📉 Blast Radius
Blast radius: Medium. Incorrect thresholding may increase analyst load and delay response.

## 🛑 Kill Switch Conditions
- Condition 1: Source false positive rate exceeds 20% for 2 consecutive days.
- Condition 2: Review queue exceeds 8 hours pending time for 3 consecutive days.

## 👤 Owner
Owner: Pilot Governance Lead

## 🧾 Seal
Seal: sha256:1d13e3d36d1f38d58a3474f53f0433c81f1f90b60eef35fbb7ec630abf0ddad4

## 🔁 Links
- Drift Issues: DRIFT-2026-001
- Patch PRs: PATCH-2026-001
