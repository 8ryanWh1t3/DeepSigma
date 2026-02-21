---
title: "Game Studio Lattice — Credibility Engine for AAA Multi-Title Governance"
version: 1.0.0
status: Example
last_updated: 2026-02-19
---

# 04 — Game Studio Lattice

**~500 nodes. Four studios. Three titles. Six decision domains. One franchise reputation.**

A multi-national AAA publisher makes thousands of creative, compliance, and commercial
decisions across studios that span four time zones. Almost none of these decisions are
structurally recorded with their reasoning, evidence, or cross-studio dependencies.

A creative director in Tokyo approves blood VFX that silently breaks PEGI 12 certification
the marketing team already promised to European retailers. A monetization change from the
Singapore live-ops team contradicts the player-first narrative Montréal's PR has been pushing
for six months. A China-specific playtime compliance patch from Bucharest introduces a
regression that blocks Sony certification globally.

These are not hypothetical failures. They are the steady-state reality of multi-studio
game development. The question is whether the institution detects them in hours or months.

---

## Guardrails

This example models a **fictional AAA publisher** called **Nexus Interactive**. All studio
names, titles, people, and data are synthetic. It demonstrates institutional credibility
architecture applied to multi-studio game development governance. No real company, game,
or platform holder is represented.

---

## 60-Second Quickstart

```bash
# from repo root

# 1) Score baseline (expected ~83 / B)
python -m coherence_ops score ./examples/04-game-studio-lattice/episodes/ --json

# 2) Ask WHY (Episode 1: rating envelope breach)
python -m coherence_ops iris query --type WHY --target ep-gs-001

# 3) Show drift inventory (expected: 4 scenario drift signals)
python -m coherence_ops iris query --type WHAT_DRIFTED --json

# 4) Run the full Drift->Patch demo (creates/prints patch plan)
python -m coherence_ops.examples.drift_patch_cycle --example game-studio

# 5) Validate example JSON is "production-shaped"
python ./examples/04-game-studio-lattice/tools/validate_example_json.py

# 6) Generate the Excel-first GameOps workbook
python ./examples/04-game-studio-lattice/tools/generate_gamestudio_workbook.py \
  --out ./examples/04-game-studio-lattice/GameOps_Workbook.xlsx
```

---

## Diagrams

Visual comprehension layer for the lattice structure and drift dynamics.

| Diagram | File | What It Shows |
|---|---|---|
| Contradiction Loop | [contradiction-loop.mmd](diagrams/contradiction-loop.mmd) | CRE -> REG -> MON -> CRE dependency cycle across all 6 domains |
| Shared Infra Blast Radius | [shared-infra-blast-radius.mmd](diagrams/shared-infra-blast-radius.mmd) | S003 + S023 cascade risk — 50 nodes, 4 domains, 18% of evidence |
| Drift to Patch | [drift-to-patch.mmd](diagrams/drift-to-patch.mmd) | Evidence -> Claims -> DriftSignal -> IRIS -> PatchPlan -> MemoryGraph sequence |

---

## The Publisher

| Attribute | Value |
|---|---|
| Publisher | Nexus Interactive (fictional) |
| Headquarters | Tokyo, Japan |
| Studios | 4 (Tokyo, Montréal, Bucharest, Singapore) |
| Active titles | 3 (franchise portfolio) |
| Decision domains | 6 |
| Lattice nodes | ~500 |
| Baseline Credibility Index | ~83 (Minor drift) |

### Studio Roles

| Studio | Location | Timezone | Primary Role | Titles |
|---|---|---|---|---|
| Nexus Tokyo | Tokyo, JP | UTC+9 | Lead development, creative authority | RONIN, VANGUARD |
| Nexus Montréal | Montréal, CA | UTC-5 | Co-development, narrative, PC platform | RONIN, SIGNAL |
| Nexus Bucharest | Bucharest, RO | UTC+2 | QA, porting, compliance testing | All titles |
| Nexus Singapore | Singapore, SG | UTC+8 | Live operations, monetization, APAC compliance | VANGUARD, SIGNAL |

### Title Portfolio

| Title | Genre | Platforms | Rating Target | Live Service | Lead Studio |
|---|---|---|---|---|---|
| **RONIN** | Action RPG | PS5, Xbox, PC, Switch | ESRB M / PEGI 16 / CERO D | Season model | Tokyo |
| **VANGUARD** | Competitive Shooter | PS5, Xbox, PC | ESRB T / PEGI 12 / CERO B | Battle pass + ranked | Tokyo + Singapore |
| **SIGNAL** | Mobile Companion | iOS, Android | ESRB E10+ / PEGI 7 / CERO A | Gacha + events | Singapore + Montréal |

---

## Decision Domains

The lattice spans six domains. Each domain has its own claims, evidence sources, and
compliance requirements — but they share sources and create cross-domain dependencies
that are invisible without formal correlation tracking.

| Domain | Code | Claims | Evidence Nodes | Primary Studios |
|---|---|---|---|---|
| Creative Direction | `CRE` | 5 (2× Tier 0) | 42 | Tokyo, Montréal |
| Regional Compliance | `REG` | 6 (3× Tier 0) | 68 | Bucharest, Singapore |
| Platform Certification | `PLT` | 4 (2× Tier 0) | 54 | Bucharest, Tokyo |
| Monetization Policy | `MON` | 5 (2× Tier 0) | 48 | Singapore, Montréal |
| Live Service Operations | `OPS` | 4 (1× Tier 0) | 38 | Singapore, Bucharest |
| Player Data Sovereignty | `DAT` | 4 (2× Tier 0) | 32 | Montréal, Bucharest |
| **Total** | | **28** | **282** | |

With 28 claims, 282 evidence nodes, 35 sources across 8 correlation groups, 4 domain
Sync Planes, and 8 beacons, the full lattice reaches approximately **500 nodes**.

---

## Lattice Structure

### Tier 0 Claims (Institutional — require K-of-N quorum, cross-studio evidence)

```
Claim-CRE-001 (Tier 0, "Franchise creative coherence across all titles")
├── SubClaim-CRE-001a ("RONIN art direction within rating envelope")
│   ├── Evidence from Tokyo art review board (Source-S001, TTL: 24h)
│   ├── Evidence from Bucharest rating pre-check (Source-S009, TTL: 12h)
│   └── Evidence from external rating board submission (Source-S021, TTL: 720h)
├── SubClaim-CRE-001b ("VANGUARD visual identity consistent with T-rating")
│   ├── Evidence from Tokyo creative leads (Source-S001, TTL: 24h)
│   └── Evidence from Montréal narrative review (Source-S005, TTL: 48h)
└── SubClaim-CRE-001c ("SIGNAL visual style age-appropriate for E10+/PEGI 7")
    ├── Evidence from Singapore art team (Source-S013, TTL: 24h)
    └── Evidence from Montréal UX review (Source-S005, TTL: 48h)

Claim-REG-001 (Tier 0, "All titles compliant with regional rating requirements")
├── SubClaim-REG-001a ("ESRB ratings valid and current for NA distribution")
├── SubClaim-REG-001b ("PEGI ratings valid for EU/UK distribution")
├── SubClaim-REG-001c ("CERO ratings valid for JP distribution")
└── SubClaim-REG-001d ("NPPA approval current for CN distribution")

Claim-REG-002 (Tier 0, "Regional monetization restrictions satisfied")
├── SubClaim-REG-002a ("Belgium/Netherlands lootbox prohibition enforced")
├── SubClaim-REG-002b ("China playtime + spending caps implemented")
├── SubClaim-REG-002c ("Japan gacha probability disclosure compliant")
└── SubClaim-REG-002d ("South Korea age-gate + spending limits active")

Claim-PLT-001 (Tier 0, "Platform certification current for all active SKUs")
├── SubClaim-PLT-001a ("Sony TRC compliance — all titles")
├── SubClaim-PLT-001b ("Microsoft XR compliance — all titles")
├── SubClaim-PLT-001c ("Nintendo Lotcheck — RONIN Switch SKU")
└── SubClaim-PLT-001d ("Steam review + Deck verification — PC SKUs")

Claim-MON-001 (Tier 0, "Monetization model consistent with public commitments")
├── SubClaim-MON-001a ("No pay-to-win mechanics in VANGUARD ranked")
├── SubClaim-MON-001b ("SIGNAL gacha rates match published probabilities")
└── SubClaim-MON-001c ("Season pass value proposition matches marketing claims")

Claim-DAT-001 (Tier 0, "Player data handling compliant across all jurisdictions")
├── SubClaim-DAT-001a ("GDPR compliance — EU player data")
├── SubClaim-DAT-001b ("CCPA compliance — California player data")
├── SubClaim-DAT-001c ("PIPL compliance — China player data")
└── SubClaim-DAT-001d ("LGPD compliance — Brazil player data")
```

### Source Inventory

| Source ID | Name | Tier | Correlation Group | Domains Fed | Evidence Count |
|---|---|---|---|---|---|
| S001 | Tokyo Art Review Board | 1 | `studio-tokyo` | CRE, PLT | 18 |
| S002 | Tokyo Engineering CI/CD | 1 | `studio-tokyo` | PLT, OPS | 14 |
| S003 | **Cross-Studio Build Pipeline** | 1 | `shared-infrastructure` | PLT, OPS, CRE | **28** |
| S005 | Montréal Narrative Review | 1 | `studio-montreal` | CRE, MON | 12 |
| S006 | Montréal Privacy Legal | 0 | `legal-compliance` | DAT, REG | 16 |
| S009 | Bucharest QA Compliance | 1 | `studio-bucharest` | REG, PLT | 22 |
| S010 | Bucharest Platform Test Lab | 1 | `studio-bucharest` | PLT | 18 |
| S013 | Singapore Live Ops Dashboard | 1 | `studio-singapore` | OPS, MON | 20 |
| S014 | Singapore Monetization Analytics | 1 | `studio-singapore` | MON, REG | 16 |
| S017 | Platform Holder Cert Portals | 0 | `external-platform` | PLT | 24 |
| S018 | Rating Board Submissions | 0 | `external-ratings` | REG, CRE | 18 |
| S021 | ESRB/PEGI/CERO Official Decisions | 0 | `external-ratings` | REG | 12 |
| S023 | Player Telemetry Pipeline | 2 | `shared-infrastructure` | OPS, MON, DAT | 22 |
| S025 | Regional Legal Counsel (external) | 0 | `legal-compliance` | REG, DAT | 14 |
| S028 | Community Sentiment Feed | 2 | `external-community` | MON, CRE | 8 |

**Key risk:** Source-S003 (Cross-Studio Build Pipeline) feeds **28 evidence nodes** across
three domains (PLT, OPS, CRE). Source-S023 (Player Telemetry Pipeline) feeds **22 nodes**
across three domains. Both are in the `shared-infrastructure` correlation group. A single
infrastructure failure cascades across 50 evidence nodes spanning 4 of 6 domains.

### Correlation Group Inventory

| Group | Sources | Domains | Evidence | Risk |
|---|---|---|---|---|
| `studio-tokyo` | S001, S002 | CRE, PLT, OPS | 32 | Medium |
| `studio-montreal` | S005, S006 | CRE, MON, DAT, REG | 28 | Medium |
| `studio-bucharest` | S009, S010 | REG, PLT | 40 | Medium |
| `studio-singapore` | S013, S014 | OPS, MON, REG | 36 | Medium |
| `shared-infrastructure` | S003, S023 | PLT, OPS, CRE, MON, DAT | **50** | **Critical** |
| `external-platform` | S017 | PLT | 24 | Low |
| `external-ratings` | S018, S021 | REG, CRE | 30 | Low |
| `legal-compliance` | S006, S025 | DAT, REG | 30 | Low |

---

## Credibility Index Walkthrough

### Component 1: Tier-Weighted Claim Integrity

11 of 12 Tier 0 claims have evidence with confidence ≥ 0.85. Claim-DAT-001c (PIPL
compliance) has a confidence of 0.78 due to recent regulatory guidance changes from
China's Cyberspace Administration that haven't been fully assessed.

Integrity score: **high with one exception**.

### Component 2: Drift Penalty

Two active drift signals at baseline:
- SIGNAL gacha rates in South Korea drifted 2.1% from published probabilities after a
  server-side config push (yellow, MON domain)
- RONIN Switch build is 3 days past Nintendo Lotcheck resubmission window (yellow, PLT domain)

Penalty: **minor** (2 yellow signals, no red).

### Component 3: Correlation Risk

`shared-infrastructure` group feeds 50 evidence nodes across 4 domains. This is the
single largest concentration risk in the lattice. If the cross-studio build pipeline
or telemetry pipeline fail, half the lattice loses evidence freshness simultaneously.

Penalty: **significant** (50-node single-group concentration).

### Component 4: Quorum Margin

Tier 0 claims generally meet K-of-N requirements. Two exceptions:
- Claim-PLT-001c (Nintendo Lotcheck) has only 2 evidence sources — one internal, one
  external. Quorum margin is thin.
- Claim-REG-002d (South Korea age-gate) relies on a single evidence source from
  Singapore. Zero quorum margin.

Penalty: **moderate** (2 thin-margin Tier 0 claims).

### Component 5: TTL Expiration

Several OPS-domain evidence nodes have 1-hour TTLs tied to live service health checks.
At any given moment, 3-5 evidence nodes are within 15 minutes of expiration. This is
normal for live-service operations but creates steady-state TTL pressure.

Penalty: **minor** (expected for live-ops domain).

### Component 6: Independent Confirmation Bonus

Claim-REG-001 (rating compliance) has evidence from 4 independent correlation groups:
`studio-bucharest`, `external-ratings`, `legal-compliance`, and `studio-singapore`.
Claim-DAT-001 (data sovereignty) has 3 independent groups.

Bonus: **moderate** (2 claims qualify).

### Composite Score

**Estimated Credibility Index: ~83 (Minor drift)**

The lattice is structurally sound but shows characteristic enterprise-scale fragility:
infrastructure correlation risk is the dominant threat vector, quorum margins are thin
on jurisdiction-specific claims, and the 14-hour timezone spread between Tokyo and
Montréal creates natural windows where drift can accumulate before the receiving
studio's workday begins.

---

## What Makes Game Studios Different

| Property | Generic Enterprise | Multi-Studio Game Publisher |
|---|---|---|
| Clock speed | Quarterly reviews | Daily builds, weekly patches, 72h cert windows |
| Contradiction cost | Audit findings | Pulled from shelves, cert failure, store delisting |
| Regional variance | Tax/employment law | Content ratings are **subjective and per-region** |
| Public exposure | B2B | Millions of players detect inconsistencies instantly |
| Platform gatekeepers | Regulators | Sony/Microsoft/Nintendo can **block distribution** |
| Monetization scrutiny | Industry norms | Legislative action (Belgium, China, Japan, Korea) |
| Creative latitude | Brand guidelines | Art direction decisions have **compliance consequences** |
| Timezone pressure | Multi-office | 14-hour gap means drift accumulates in overnight windows |

The core insight: **creative decisions have compliance consequences, compliance
decisions have commercial consequences, and commercial decisions have creative
consequences.** The dependency loops are tighter and faster than in most industries.

---

## Node Inventory

| Type | Count | IDs |
|---|---|---|
| Claim (Tier 0) | 12 | CRE-001, CRE-002, REG-001, REG-002, REG-003, PLT-001, PLT-002, MON-001, MON-002, OPS-001, DAT-001, DAT-002 |
| Claim (Tier 1-2) | 16 | CRE-003 through CRE-005, REG-004 through REG-006, PLT-003, PLT-004, MON-003 through MON-005, OPS-002 through OPS-004, DAT-003, DAT-004 |
| SubClaim | 84 | ~3 per claim average |
| Evidence | 282 | Distributed across 6 domains |
| Source | 35 | 15 primary (listed above) + 20 secondary |
| Correlation Group | 8 | Listed above |
| Sync Plane | 4 | One per studio timezone region |
| Sync Beacon | 8 | 2 per Sync Plane (internal + external) |
| **Total** | **~499** | |

---

## Key Observations

**Shared build infrastructure is the dominant risk.** Source-S003 and S023 together feed
50 evidence nodes — 18% of all evidence — across 4 of 6 domains. The `shared-infrastructure`
correlation group is the single point of failure that would cascade most broadly.

**Rating board decisions are slow evidence.** ESRB, PEGI, and CERO decisions have TTLs
measured in months, but when a creative decision invalidates a rating, the *detection*
of that invalidation depends on fast-TTL sources (internal QA, art review). The lattice
captures this temporal mismatch explicitly.

**Timezone creates natural drift windows.** Between 18:00 UTC (end of Montréal workday)
and 00:00 UTC (start of Tokyo workday), there is a 6-hour gap where drift signals from
live operations in Singapore accumulate with no creative authority available to assess them.
The Sync Plane makes this gap visible; without it, drift is silent overnight.

**Monetization is the highest-contradiction domain.** The intersection of player-facing
commitments ("no pay-to-win"), regional legal requirements (Belgium lootbox ban, Japan
gacha disclosure), and revenue targets creates a three-way tension that generates drift
signals at a higher rate than any other domain.

**Platform certification is binary and unforgiving.** Unlike compliance (which has
remediation windows), Sony TRC and Nintendo Lotcheck failures are pass/fail gates that
block distribution. A single claim failure in PLT domain has immediate commercial impact
across all regions where that platform operates.

---

## Try It

See [60-Second Quickstart](#60-second-quickstart) above, or the full [Runbook](RUNBOOK.md) for step-by-step procedures.

```bash
# Score all episodes
python -m coherence_ops score ./examples/04-game-studio-lattice/episodes/ --json

# IRIS: why was the rating envelope breached?
python -m coherence_ops iris query --type WHY --target ep-gs-001

# IRIS: what drifted?
python -m coherence_ops iris query --type WHAT_DRIFTED --json

# Full Drift->Patch cycle
python -m coherence_ops.examples.drift_patch_cycle --example game-studio

# Validate all example JSON
python ./examples/04-game-studio-lattice/tools/validate_example_json.py

# Generate GameOps Excel workbook
python ./examples/04-game-studio-lattice/tools/generate_gamestudio_workbook.py \
  --out ./examples/04-game-studio-lattice/GameOps_Workbook.xlsx
```

---

→ [Scenario Plan](SCENARIO_PLAN.md) · [Schemas](SCHEMAS.md) · [Runbook](RUNBOOK.md) · [IRIS Queries](iris_queries.md) · [Diagrams](diagrams/)
