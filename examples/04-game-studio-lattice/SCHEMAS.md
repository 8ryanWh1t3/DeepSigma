---
title: "Game Studio Lattice — Schema Reference"
version: 1.0.0
status: Example
last_updated: 2026-02-19
---

# Game Studio Lattice Schema Reference

Schema structures for multi-studio AAA game development lattice entities. These schemas
extend the Enterprise Lattice schemas with game-industry-specific fields for rating
compliance, platform certification, monetization governance, and multi-title portfolio
management.

---

## Evidence Node (Game Studio Extension)

Every evidence node carries the core fields plus game-studio-specific context.

```json
{
  "element_id": "Evidence-REG-E014",
  "status": "OK",
  "tier": 0,
  "event_time": "2026-02-18T09:00:00Z",
  "ingest_time": "2026-02-18T09:00:04Z",
  "ttl": "PT720H",
  "source_id": "Source-S021",
  "confidence": 0.97,
  "signature": "sha256:7f2a9b...",
  "correlation_group": "external-ratings",
  "mode": "direct",
  "domain": "REG",
  "studio_origin": "bucharest",
  "title": "RONIN",
  "sku": "RONIN-PS5-EU",
  "rating_board": "PEGI",
  "rating_decision": "PEGI-16",
  "region": "EU",
  "platform": null,
  "content_descriptors": ["violence", "blood"],
  "decision_reference": "PEGI-2026-NI-00347"
}
```

### Game Studio Extension Fields

| Field | Required | Constraints |
|---|---|---|
| studio_origin | Yes | tokyo · montreal · bucharest · singapore |
| title | Yes | RONIN · VANGUARD · SIGNAL · ALL |
| sku | If platform-specific | Format: `{TITLE}-{PLATFORM}-{REGION}` |
| rating_board | REG domain | ESRB · PEGI · CERO · NPPA · GRAC · USK |
| rating_decision | REG domain | Board-specific rating code |
| region | If region-specific | ISO 3166-1 alpha-2 or region group (EU, NA, APAC, CN) |
| platform | PLT domain | PS5 · XBOX · SWITCH · PC-STEAM · PC-EPIC · IOS · ANDROID |
| content_descriptors | CRE+REG domains | Array of content tags |
| decision_reference | If external | External authority reference number |

---

## Source Registry (Game Studio)

Sources include studio affiliation and title coverage.

```json
{
  "source_id": "Source-S003",
  "name": "Cross-Studio Build Pipeline",
  "tier": 1,
  "correlation_group": "shared-infrastructure",
  "domains": ["PLT", "OPS", "CRE"],
  "studios": ["tokyo", "montreal", "bucharest", "singapore"],
  "titles": ["RONIN", "VANGUARD", "SIGNAL"],
  "evidence_count": 28,
  "refresh_cadence": "PT1H",
  "status": "active",
  "last_seen": "2026-02-19T13:45:00Z",
  "infrastructure_type": "ci-cd",
  "shared_cluster": "k8s-global-prod-01",
  "failover": null
}
```

```json
{
  "source_id": "Source-S017",
  "name": "Platform Holder Cert Portals",
  "tier": 0,
  "correlation_group": "external-platform",
  "domains": ["PLT"],
  "studios": ["bucharest"],
  "titles": ["RONIN", "VANGUARD", "SIGNAL"],
  "evidence_count": 24,
  "refresh_cadence": "PT24H",
  "status": "active",
  "last_seen": "2026-02-19T08:00:00Z",
  "infrastructure_type": "external-portal",
  "platform_holders": ["sony", "microsoft", "nintendo", "valve"],
  "cert_types": ["TRC", "XR", "lotcheck", "steam-review"]
}
```

---

## Claim Structure (Game Studio)

Claims include title scope and cross-studio quorum requirements.

```json
{
  "claim_id": "Claim-REG-001",
  "domain": "REG",
  "tier": 0,
  "title_scope": "ALL",
  "statement": "All titles compliant with regional rating requirements",
  "subclaims": [
    "SubClaim-REG-001a",
    "SubClaim-REG-001b",
    "SubClaim-REG-001c",
    "SubClaim-REG-001d"
  ],
  "quorum": {
    "n": 16,
    "k": 12,
    "min_correlation_groups": 3,
    "requires_tier_0_source": true,
    "requires_external_authority": true
  },
  "status": "OK",
  "credibility_sub_index": 88,
  "rating_boards_covered": ["ESRB", "PEGI", "CERO", "NPPA"],
  "regions_covered": ["NA", "EU", "JP", "CN"],
  "last_board_decision": "2026-02-18T09:00:00Z",
  "next_submission_due": "2026-03-01T00:00:00Z"
}
```

```json
{
  "claim_id": "Claim-MON-001",
  "domain": "MON",
  "tier": 0,
  "title_scope": "ALL",
  "statement": "Monetization model consistent with public commitments",
  "subclaims": [
    "SubClaim-MON-001a",
    "SubClaim-MON-001b",
    "SubClaim-MON-001c"
  ],
  "quorum": {
    "n": 12,
    "k": 8,
    "min_correlation_groups": 2,
    "requires_tier_0_source": false,
    "requires_external_authority": false
  },
  "status": "DEGRADED",
  "credibility_sub_index": 71,
  "public_commitments": [
    {
      "id": "PC-MON-001",
      "source": "VANGUARD Player-First Promise blog post",
      "date": "2026-01-28",
      "claim": "No competitive content behind randomized purchases",
      "studio_origin": "montreal",
      "url_reference": "nexus-interactive.com/blog/player-first-promise"
    }
  ],
  "regional_restrictions": [
    {"region": "BE", "restriction": "No paid random rewards", "authority": "Belgian Gaming Commission"},
    {"region": "NL", "restriction": "No paid random rewards", "authority": "Kansspelautoriteit"},
    {"region": "JP", "restriction": "Probability disclosure required", "authority": "Consumer Affairs Agency"},
    {"region": "KR", "restriction": "Age-gate + spending limits", "authority": "Game Rating and Administration Committee"},
    {"region": "CN", "restriction": "Playtime caps + spending caps + probability disclosure", "authority": "NPPA"}
  ]
}
```

---

## Platform Certification Record

Tracks per-SKU certification status with platform-specific requirements.

```json
{
  "cert_id": "CERT-RONIN-PS5-001",
  "claim_id": "Claim-PLT-001",
  "title": "RONIN",
  "platform": "PS5",
  "platform_holder": "sony",
  "cert_type": "TRC",
  "version": "1.04.2",
  "build_id": "ronin-ps5-20260218-nightly-4a7b",
  "submission_date": "2026-02-15T00:00:00Z",
  "status": "passed",
  "result_date": "2026-02-18T14:00:00Z",
  "issues": [],
  "ttl": "PT2160H",
  "next_submission_trigger": "any_content_change_or_90d",
  "evidence_ids": ["Evidence-PLT-E003", "Evidence-PLT-E004"],
  "source_id": "Source-S017",
  "region_scope": "global"
}
```

```json
{
  "cert_id": "CERT-RONIN-SWITCH-001",
  "claim_id": "Claim-PLT-001",
  "title": "RONIN",
  "platform": "SWITCH",
  "platform_holder": "nintendo",
  "cert_type": "lotcheck",
  "version": "1.04.1",
  "build_id": "ronin-switch-20260210-release-2c3d",
  "submission_date": "2026-02-10T00:00:00Z",
  "status": "failed",
  "result_date": "2026-02-14T11:00:00Z",
  "issues": [
    {
      "issue_id": "LC-2026-0891",
      "category": "performance",
      "description": "Frame rate drops below 20fps during chapter 7 boss encounter",
      "severity": "must-fix",
      "resubmission_required": true
    }
  ],
  "ttl": "PT168H",
  "next_submission_trigger": "resubmission_required",
  "evidence_ids": ["Evidence-PLT-E007"],
  "source_id": "Source-S017",
  "region_scope": "global"
}
```

---

## Drift Signal (Game Studio)

Game studio drift signals include title and cross-studio context.

```json
{
  "ds_id": "DS-GS-001",
  "episode_id": "ep-gs-001",
  "category": "content_rating_mismatch",
  "severity": "red",
  "detected_at": "2026-02-19T07:30:00Z",
  "domains_affected": ["CRE", "REG", "PLT"],
  "affected_claims": ["Claim-CRE-001", "Claim-REG-001", "Claim-PLT-001"],
  "affected_evidence_count": 18,
  "title": "RONIN",
  "sku_affected": ["RONIN-PS5-EU", "RONIN-XBOX-EU", "RONIN-PC-EU", "RONIN-SWITCH-GLOBAL"],
  "studios_involved": {
    "origin": "tokyo",
    "detection": "bucharest",
    "impact": ["montreal"]
  },
  "source_id": "Source-S009",
  "correlation_group": "studio-bucharest",
  "runtime_types": ["verify", "outcome"],
  "cross_domain": true,
  "cross_studio": true,
  "rating_impact": {
    "current_rating": "PEGI-16",
    "detected_rating": "PEGI-18",
    "boards_affected": ["PEGI", "CERO"],
    "retail_commitments_at_risk": true
  },
  "credibility_index_impact": {
    "before": 83,
    "after": 64,
    "delta": -19
  },
  "timezone_context": {
    "origin_local_time": "14:00 JST",
    "detection_local_time": "09:30 EET",
    "hours_to_detection": 2.5,
    "studios_in_business_hours": ["bucharest", "montreal"],
    "studios_after_hours": []
  }
}
```

```json
{
  "ds_id": "DS-GS-003",
  "episode_id": "ep-gs-003",
  "category": "shared_infrastructure_cascade",
  "severity": "red",
  "detected_at": "2026-02-20T08:00:00Z",
  "domains_affected": ["PLT", "OPS", "CRE", "MON", "DAT"],
  "affected_claims": [
    "Claim-PLT-001", "Claim-PLT-002",
    "Claim-OPS-001",
    "Claim-CRE-001",
    "Claim-MON-003",
    "Claim-DAT-003"
  ],
  "affected_evidence_count": 50,
  "title": "ALL",
  "studios_involved": {
    "origin": "shared-infrastructure",
    "detection": "automated",
    "impact": ["tokyo", "montreal", "bucharest", "singapore"]
  },
  "source_ids": ["Source-S003", "Source-S023"],
  "correlation_group": "shared-infrastructure",
  "runtime_types": ["verify", "time"],
  "cross_domain": true,
  "cross_studio": true,
  "cascade": {
    "trigger": "CI/CD dependency binary incompatibility",
    "trigger_time": "2026-02-20T08:00:00Z",
    "propagation": [
      {"source": "S003", "time": "T+0m", "domains": ["PLT", "OPS", "CRE"], "evidence_lost": 28},
      {"source": "S023", "time": "T+30m", "domains": ["OPS", "MON", "DAT"], "evidence_lost": 22}
    ],
    "total_evidence_affected": 50,
    "domains_affected_count": 5,
    "peak_index_drop": -28
  },
  "credibility_index_impact": {
    "before": 71,
    "after": 41,
    "delta": -30
  }
}
```

---

## Sync Plane (Game Studio — Timezone-Aware)

Each studio operates its own Sync Plane, with cross-studio beacon comparison detecting
timezone-amplified drift.

```json
{
  "sync_plane_id": "sync-singapore",
  "studio": "singapore",
  "timezone": "UTC+8",
  "business_hours": {"start": "09:00", "end": "18:00", "local_tz": "Asia/Singapore"},
  "domains_primary": ["OPS", "MON"],
  "beacons": [
    {
      "beacon_id": "Beacon-SG1",
      "type": "internal",
      "tier": 1,
      "status": "active",
      "last_heartbeat": "2026-02-19T13:59:30Z"
    },
    {
      "beacon_id": "Beacon-SG2",
      "type": "external",
      "tier": 0,
      "status": "active",
      "last_heartbeat": "2026-02-19T13:59:28Z"
    }
  ],
  "sync_nodes": 4,
  "watermark": "2026-02-19T13:59:00Z",
  "watermark_cadence": "PT30S",
  "cross_studio_sync": {
    "paired_planes": ["sync-tokyo", "sync-montreal", "sync-bucharest"],
    "max_acceptable_divergence": "PT2H",
    "current_divergence": {
      "sync-tokyo": "PT0S",
      "sync-montreal": "PT0S",
      "sync-bucharest": "PT0S"
    },
    "overnight_gap_detection": true,
    "escalation_threshold": "PT4H"
  }
}
```

---

## Decision Episode (Game Studio)

Sealed episodes include multi-studio, multi-title context.

```json
{
  "episode_id": "ep-gs-002",
  "title": "VANGUARD",
  "domain_primary": "MON",
  "domains_affected": ["MON", "REG", "CRE"],
  "severity": "red",
  "studios_involved": ["singapore", "bucharest", "montreal"],
  "detected_at": "2026-02-19T13:00:00Z",
  "resolved_at": "2026-02-20T13:00:00Z",
  "resolution_hours": 24,
  "dlr": {
    "decision": "Disable Founder's Cache in restricted regions; remove stat variations; publish player communication",
    "decided_by": "Cross-studio governance council",
    "authority_level": "publisher",
    "evidence_considered": 14,
    "alternatives_rejected": [
      "Keep Cache globally with probability disclosure only (rejected: does not resolve Belgium/Netherlands)",
      "Remove Cache entirely (rejected: creates different CRE drift — promised content not delivered)"
    ]
  },
  "rs": {
    "primary_reasoning": "Three-way contradiction loop requires sequenced resolution: regulatory first, then commercial, then narrative",
    "weights": {
      "regulatory_urgency": 0.45,
      "player_trust": 0.30,
      "revenue_impact": 0.15,
      "timeline_pressure": 0.10
    },
    "counter_claims": [
      "Revenue team argued Cache could be retained in unrestricted regions (accepted for non-BE/NL/KR/CN)",
      "PR team argued immediate full removal would signal panic (accepted — sequenced approach preferred)"
    ]
  },
  "ds": {
    "drift_signals": ["DS-GS-002a", "DS-GS-002b", "DS-GS-002c"],
    "categories": ["policy_breach", "narrative_integrity", "regional_violation"],
    "cascade_detected": true,
    "cascade_type": "three-way contradiction loop"
  },
  "mg": {
    "new_edges": [
      "Singapore monetization approval → Bucharest compliance pre-check",
      "Singapore monetization approval → Montréal PR consistency review",
      "Public commitment registry → monetization feature approval gate"
    ],
    "governance_changes": 3,
    "templates_updated": ["monetization_approval_v2", "regional_compliance_checklist_v3"]
  },
  "seal": {
    "hash": "sha256:c4f8a2d7e1b9...",
    "sealed_at": "2026-02-20T13:15:00Z",
    "sealed_by": "coherence_steward",
    "integrity": "verified"
  }
}
```

---

## Relationship to Existing Schemas

| Game Studio Schema | Extends | Game-Specific Additions |
|---|---|---|
| Evidence node | Core System Design + Enterprise domain | studio_origin, title, sku, rating_board, platform, content_descriptors |
| Source registry | Enterprise source | studios, titles, infrastructure_type, platform_holders |
| Claim | Enterprise claim + quorum | title_scope, public_commitments, regional_restrictions, rating_boards_covered |
| Certification record | *New* | Platform-specific cert tracking with pass/fail gates |
| Drift signal | Enterprise drift | title, sku_affected, studios_involved, rating_impact, timezone_context, cascade |
| Sync Plane | Enterprise Sync Plane | timezone, business_hours, cross_studio_sync, overnight_gap_detection |
| Decision Episode | Core episode | multi-studio DLR, title context, governance_changes |
