---
title: "Drift to Patch Workflow"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Drift to Patch Workflow

## Overview

After every episode is sealed, the Drift Detector scans for anomalies. If found, it emits a typed DriftSignal, checks for recurrence, and triggers the patch workflow.

## Step 1: Drift Detection

| Check | Drift Type |
|-------|-----------|
| totalMs > dte.deadlineMs | time |
| Any claim age > ttlMs | freshness |
| degradeStep != ideal | fallback |
| Required gate skipped | bypass |
| verification.passed == false | verify |
| outcome.code unexpected | outcome |
| Hop count exceeds limit | fanout |
| Lock/IO wait exceeds threshold | contention |

## Step 2: Drift Signal Emission

Each anomaly produces a DS record with driftType, severity, evidenceRefs, recommendedPatchType, and a fingerprint for recurrence tracking.

## Step 3: Fingerprint and Recurrence

The fingerprint.key is a stable identifier for this class of drift. The system queries MG for previous occurrences.

- 1st occurrence: log and monitor
- - 2nd occurrence: escalate to at least yellow
  - - 3rd+ occurrence: escalate to red, trigger patch workflow
   
    - ## Step 4: Patch Proposal
   
    - A patch specifies: what to change, from what value to what value, and why.
   
    - ## Step 5: Patch Approval
   
    - | Condition | Approval Mode |
    - |-----------|--------------|
    - | severity green AND blastRadius low | Auto-apply |
    - | severity yellow | Auto-apply with notification |
    - | severity red | Human review required |
    - | Any blastRadius high | Human review required |
   
    - ## Step 6: Memory Graph Update
   
    - After patch application:
    - 1. Patch node added to MG
      2. 2. Edge PATCHED_BY from DriftSignal to Patch
         3. 3. Edge INFORMED from Patch to subsequent episodes
            4. 4. RS picks up the patch in next reflection session
              
               5. The loop is closed. Next decision uses updated policy.
