---
title: "Drift to Patch Conceptual Model"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Drift to Patch Conceptual Model

## Core Idea

Decisions are not static. The conditions under which they were made change over time. Drift is the formal name for this change. Patch is the formal name for the correction.

## Drift Taxonomy

| Drift Type | What Changed | Detection Method |
|------------|-------------|-----------------|
| `time` | Decision took longer than allowed | `totalMs > dte.deadlineMs` |
| `freshness` | Input data went stale | `claim.age > claim.ttlMs` |
| `fallback` | System couldn't use ideal path | `degradeStep != "ideal"` |
| `bypass` | Required gate was skipped | Missing verification or auth step |
| `verify` | Post-condition check failed | `verification.passed == false` |
| `outcome` | Result wasn't what was expected | `outcome.code != expected` |
| `fanout` | Too many hops or parallel calls | `hopCount > limit` |
| `contention` | Resource bottleneck | `lockWaitMs > threshold` |

## Patch Taxonomy

| Patch Type | What It Fixes | Example |
|------------|--------------|---------|
| `dte_change` | Deadline or budget too tight/loose | Increase deadline from 2000ms to 3000ms |
| `ttl_change` | TTL too aggressive/permissive | Increase credit_score TTL from 30s to 60s |
| `cache_bundle_change` | Cache strategy needs update | Add geo_risk to pre-warm bundle |
| `routing_change` | Wrong data source or path | Switch to faster credit score API |
| `verification_change` | Verification method inadequate | Add invariant check alongside read-after-write |
| `action_scope_tighten` | Action blast radius too broad | Require L3 auth for multi-account quarantine |
| `manual_review` | System cannot auto-correct | Flag for human decision on policy change |

## Recurrence and Escalation

Drift fingerprints enable recurrence tracking. The same class of drift is tracked across episodes. Escalation rules ensure that recurring drift gets progressively more attention until it is patched.

Severity escalation:
- 1st occurrence: severity stays as detected, log only
- - 2nd occurrence: severity escalates to at least `yellow`
  - - 3rd+ occurrence: severity escalates to `red`, patch workflow triggered
