# pyDOGE Architecture

## Operating thesis

```text
MAKE THE SYSTEM EXPLAINABLE BEFORE OPTIMIZING IT
```

Canonical diagnostic chain:

```text
MISSION
  ↓
AUTHORITY
  ↓
POLICY
  ↓
WORK
  ↓
DEPENDENCIES
  ↓
SYSTEMS
  ↓
PEOPLE / ROLE CAPACITY
  ↓
OUTCOME
```

`RoleCapacity` exists to estimate capacity/cost at the work-system level. It is not an employee-performance object.

## Analysis surfaces

| Surface | Question |
|---|---|
| Mission binding | Why does the work exist? |
| Authority trace | Who/what authorizes the requirement? |
| Policy lineage | What rule generates the work? |
| Dependency graph | What relies on it? |
| Blast radius | What changes if it changes? |
| Handoff latency | Where is work waiting rather than being worked? |
| Rework | Where is work being repeated? |
| Duplicate candidate | Are multiple workflows producing substantially the same output? |
| Orphan work | Does work exist without mission/policy justification? |
| Drift | Did observed outcomes diverge from expectations? |
| Automation candidate | After work is justified, is it bounded enough to automate? |

## Intervention order

```text
VALIDATE → CONSOLIDATE → REDESIGN → PATCH → AUTOMATE → SIZE
```

The sequence is intentional. `SIZE` is last.

## CERPA bridge

The included minimal ledger preserves the Deep Sigma loop:

```text
CLAIM → EVENT → REVIEW → PATCH → APPLY
```

The library does not autonomously authorize `APPLY`; the ledger records the state transition supplied by the consuming application.

## Guardrails

1. No employee scoring.
2. No individual productivity ranking.
3. No automation of orphan work before mission/policy validation.
4. Automation findings are candidates, not authorization.
5. Duplicate findings require human confirmation.
6. Workforce capacity is downstream of redesigned work.
