---
title: "Coherence SLOs"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Coherence SLOs

Service Level Objectives for Institutional Decision Infrastructure.

## SLO Table

| SLO | Target | Measurement |
|-----|--------|-------------|
| Decision Freshness | 95% of decisions use claims within TTL | claims_within_ttl / total_claims per episode |
| Decision Timeliness | 99% within DTE deadline | totalMs <= dte.deadlineMs |
| Verification Rate | 100% of high-blast-radius actions verified | verification.passed != null for blastRadius >= medium |
| Seal Integrity | 100% pass hash verification | computed_hash == seal.hash |
| Drift Response Time | RED drift patched within 4 hours | patch.appliedAt - drift.detectedAt |
| Memory Queryability | IRIS WHY queries in < 60 seconds | IRIS response time |
| Coherence Score | Rolling 7-day average >= 75/100 | CoherenceScorer output |
| Ideal Path Rate | >= 80% on ideal path | degradeStep == ideal |

## Scoring Model

The CoherenceScorer produces a 0-100 score across three dimensions:

| Dimension | Weight | Inputs |
|-----------|--------|--------|
| Truth | 35% | Claim freshness, confidence distribution, evidence coverage |
| Reasoning | 35% | Ideal path rate, degrade step distribution, verification pass rate |
| Memory | 30% | MG completeness, drift response time, patch application rate |

Grade mapping: A (90-100), B (80-89), C (70-79), D (60-69), F (below 60).
