# AltCogOps → pyAltCog Mapping

| AltCogOps construct | pyAltCog implementation |
|---|---|
| Friction → Anomaly → Signal → Cluster → Hypothesis → Test → AltCog → Monitor → Promote | `AltCogEngine`, `MaturityState`, `lifecycle.py` |
| AC0–AC8 | `MaturityState` enum |
| Outcome mismatch | `DiscoverySurface.OUTCOME_MISMATCH` |
| Residual evidence | `DiscoverySurface.RESIDUAL_EVIDENCE` |
| Repeated exception | `DiscoverySurface.REPEATED_EXCEPTION` |
| Cross-source contradiction | `DiscoverySurface.CROSS_SOURCE_CONTRADICTION` |
| Assumption dependence | `DiscoverySurface.ASSUMPTION_DEPENDENCE` |
| Edge-case accumulation | `DiscoverySurface.EDGE_CASE_ACCUMULATION` |
| Cross-domain analogy | `DiscoverySurface.CROSS_DOMAIN_ANALOGY` |
| ALT-F13 Friction Signal Capture | `DiscoveryFunction.F13_FRICTION_SIGNAL_CAPTURE` |
| ALT-F14 Residual Detection | `DiscoveryFunction.F14_RESIDUAL_DETECTION` |
| ALT-F15 Exception Clustering | `DiscoveryFunction.F15_EXCEPTION_CLUSTERING` |
| ALT-F16 Alternative Candidate Promotion | `DiscoveryFunction.F16_ALTERNATIVE_CANDIDATE_PROMOTION` |
| ALT-F17 Discriminating Evidence Planner | `DiscoveryFunction.F17_DISCRIMINATING_EVIDENCE_PLANNER` |
| ALT-F18 Dormant Alternative Monitoring | `DiscoveryFunction.F18_DORMANT_ALTERNATIVE_MONITORING` |
| ALT-E13…ALT-E18 | `DiscoveryEvent` enum |
| FSR | `FrictionSignalRecord` |
| RER | `ResidualEvidenceRecord` |
| ECC | `ExceptionClusterCard` |
| ACP | `AltCogCandidatePacket` |
| DEP | `DiscriminatingEvidencePlan` |
| DAM | `DormantAlternativeMonitor` |
| ADR | `altcog_discovery_rate` |
| RCR | `residual_conversion_rate` |
| WPR | `weak_signal_promotion_rate` |
| TAF | `time_to_alternative_formation` |
| DAR | `dormant_alternative_recall` |

## AC6 operational gate

A candidate becomes an operational AltCog only when it has:

- a dominant model it challenges;
- at least one supporting signal;
- a distinct prediction;
- a falsification condition / evidence plan;
- sufficient mission relevance;
- an owner;
- a revisit trigger;
- an explicit score meeting the configured promotion threshold.

Rejected alternatives are archived, not deleted.
