# EDGE + ABP

> **Exportable Decision Governance Engine** — self-contained HTML modules with embedded Authority Boundary Primitives for offline-capable, verifiable decision surfaces.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Module Inventory](#module-inventory)
- [Quick Reference](#quick-reference)
- [Wiki](#wiki)

---

## Overview

**EDGE** modules are standalone HTML files that bundle an entire decision surface — UI, logic, data, and governance — into a single distributable artifact. Each EDGE export embeds a signed **ABP** (Authority Boundary Primitive) that declares what the module is allowed to do, what data it can access, and what proof it must produce.

The system enforces a closed loop:

1. **Build ABP** — declare authority boundaries (scope, objectives, tools, data, approvals, escalation, runtime validators, proof requirements)
2. **Embed in EDGE** — stamp each HTML export with the ABP in a `<script type="application/json" id="ds-abp-v1">` block
3. **Gate before distribution** — `gate_abp.py` runs 10 checks per file (hash, ID, scope, contradictions, status bar, verification JS, delegation review)
4. **Verify independently** — `verify_abp.py` runs 8 structural checks; `verify_pack.py` validates the full admissibility pack
5. **Reassess via delegation review** — sustained drift triggers formal ABP reassessment (DRT-001 through DRT-004)

## Architecture

```mermaid
flowchart TD
    subgraph Authority["Authority Layer"]
        LEDGER["Authority Ledger\n(NDJSON, hash-chained)"]
        POLICY["Governance Policy\n(GOV-x.y.z)"]
    end

    subgraph Build["ABP Build"]
        SCOPE["Scope\n(contract, program, modules)"]
        CONFIG["ABP Config\n(objectives, tools, data,\napprovals, escalation,\nruntime, proof, delegation)"]
        BUILDER["build_abp.py\n- Deterministic ID\n- Content hash\n- Contradiction check"]
    end

    subgraph Artifact["ABP Artifact"]
        ABP["abp_v1.json\nABP-bf0afe15\nsha256:c01f..."]
    end

    subgraph EDGE["EDGE Modules (8)"]
        UNI["Unified\n(8 tabs)"]
        HIR["Hiring UI"]
        BID["Bid/NoBid UI"]
        CMP["Compliance Matrix"]
        BOE["BOE Pricing"]
        AWD["Award Staffing"]
        COH["Coherence Dashboard"]
        SRO["Suite ReadOnly"]
    end

    subgraph Gate["Gate Enforcement"]
        GATE["gate_abp.py\n10 checks per file\n80/80 total"]
    end

    subgraph Verify["Verification"]
        VABP["verify_abp.py\n8 checks"]
        VPACK["verify_pack.py\n--require-abp"]
    end

    subgraph Reassess["Delegation Review"]
        DRIFT["Drift Telemetry\n(DS events)"]
        TRIGGER["4 DRT Triggers\n(warn / critical)"]
        REVIEW["Reviewer\napproves patch"]
    end

    LEDGER --> BUILDER
    POLICY --> BUILDER
    SCOPE --> BUILDER
    CONFIG --> BUILDER
    BUILDER --> ABP

    ABP --> UNI & HIR & BID & CMP & BOE & AWD & COH & SRO

    UNI & HIR & BID & CMP & BOE & AWD & COH & SRO --> GATE
    GATE -->|"ALL PASS"| DIST["Distribution"]
    GATE -->|"ANY FAIL"| BLOCK["Blocked"]

    ABP --> VABP
    ABP --> VPACK

    DRIFT --> TRIGGER
    TRIGGER -->|"threshold met"| REVIEW
    REVIEW -->|"abp_patch"| BUILDER

    style Authority fill:#e7f5ff,stroke:#1c7ed6
    style Build fill:#fff3bf,stroke:#f59f00
    style Artifact fill:#d3f9d8,stroke:#37b24d
    style EDGE fill:#e8f5e9,stroke:#43a047
    style Gate fill:#fff3e0,stroke:#fb8c00
    style Verify fill:#e3f2fd,stroke:#1e88e5
    style Reassess fill:#fce4ec,stroke:#e53935
    style BLOCK fill:#ff6b6b,color:#fff
    style DIST fill:#51cf66,color:#fff
```

## Module Inventory

| File | Version | Module Key | Purpose |
|------|---------|------------|---------|
| `EDGE_Unified_v1.0.0.html` | 1.0.0 | `unified` | Unified control surface — 8 tabs: Suite, Hiring, Bid, Compliance, BOE, IRIS, Delegation, Utility |
| `EDGE_Coherence_Dashboard_v2.0.0.html` | 2.0.0 | `coherence` | Coherence monitoring — CI gauge, claims, drift signals, analysis visualizations |
| `EDGE_Hiring_UI_v1.0.0.html` | 1.0.0 | `hiring` | Hiring console — form-driven staffing intake and candidate tracking |
| `EDGE_BidNoBid_UI_v1.0.0.html` | 1.0.0 | `bid` | Bid/no-bid decision matrix — opportunity evaluation and scoring |
| `EDGE_BOE_Pricing_UI_v1.0.0.html` | 1.0.0 | `boe` | Basis-of-estimate pricing models and rate calculations |
| `EDGE_ComplianceMatrix_UI_v1.0.0.html` | 1.0.0 | `compliance` | Compliance requirements mapped to deliverables |
| `EDGE_AwardStaffing_Estimator_v1.2.0.html` | 1.2.0 | `award_staffing` | Award staffing allocation and cost estimation |
| `EDGE_Suite_ReadOnly_v1.0.0.html` | 1.0.0 | `suite_readonly` | Read-only wrapper with telemetry and rollup export |

### Supporting Files

| File | Purpose |
|------|---------|
| `abp_v1.json` | Reference ABP artifact (ABP-bf0afe15) |
| `gate_abp.py` | Gate enforcement CLI — verifies all EDGE exports carry valid ABP |

## Quick Reference

```bash
# Build ABP from config
python enterprise/src/tools/reconstruct/build_abp.py \
    --scope '{"contract_id":"CTR-DEMO-001","program":"SEQUOIA","modules":["hiring","bid","compliance","boe","award_staffing","coherence","suite_readonly","unified"]}' \
    --authority-entry-id AUTH-033059a5 \
    --authority-ledger enterprise/artifacts/public_demo_pack/authority_ledger.ndjson \
    --config abp_config.json \
    --clock 2026-02-25T00:00:00Z \
    --out-dir edge/

# Gate-check all EDGE exports
python edge/gate_abp.py --dir edge/ --abp-ref edge/abp_v1.json

# Gate-check single file
python edge/gate_abp.py --file edge/EDGE_Hiring_UI_v1.0.0.html

# Gate-check with JSON output
python edge/gate_abp.py --dir edge/ --json

# Verify ABP standalone
python enterprise/src/tools/reconstruct/verify_abp.py \
    --abp edge/abp_v1.json \
    --ledger enterprise/artifacts/public_demo_pack/authority_ledger.ndjson

# Verify full evidence pack (with ABP requirement)
python enterprise/src/tools/reconstruct/verify_pack.py \
    --pack /tmp/pack --require-abp

# Run ABP tests
python -m pytest enterprise/tests/test_build_abp.py -v
```

## Authoring Policy

All files in `edge/` are **hand-authored artifacts**. They are not generated by CI
or code-gen tooling. Changes to EDGE HTML modules or the ABP reference file must be:

1. **Reviewed** — every PR touching `edge/*.html` or `edge/*.json` requires human review
2. **Gate-checked** — `python edge/gate_abp.py --dir edge/` must pass before merge
3. **Version-bumped** — update the filename version suffix when modifying an EDGE module
4. **ABP-consistent** — if the ABP scope changes, re-stamp all EDGE modules

These files are marked `linguist-vendored` in `.gitattributes` so they do not
inflate language statistics on GitHub.

## Wiki

Deep-dive reference pages (synced to [GitHub Wiki](https://github.com/8ryanWh1t3/DeepSigma/wiki)):

| Page | Topic |
|------|-------|
| [EDGE Modules](https://github.com/8ryanWh1t3/DeepSigma/wiki/EDGE-Modules) | All 8 modules, Unified tabs, Coherence Dashboard, localStorage keys |
| [ABP Specification](https://github.com/8ryanWh1t3/DeepSigma/wiki/ABP-Specification) | Full structure, deterministic ID/hash, canonical JSON, composition, sections reference |
| [Delegation Review](https://github.com/8ryanWh1t3/DeepSigma/wiki/Delegation-Review) | Governance loop, 4 DRT triggers, review policy, client-side evaluation |
| [Gate Enforcement](https://github.com/8ryanWh1t3/DeepSigma/wiki/Gate-Enforcement) | gate_abp.py, 10 checks, file-to-module map, CLI, JSON output |
| [ABP Verification](https://github.com/8ryanWh1t3/DeepSigma/wiki/ABP-Verification) | verify_abp.py 8 checks, verify_pack.py integration, evidence pack |
| [ABP Builder](https://github.com/8ryanWh1t3/DeepSigma/wiki/ABP-Builder) | build_abp(), compose_abps(), CLI, HTML embedding, re-stamping |
| [Authority Ledger Binding](https://github.com/8ryanWh1t3/DeepSigma/wiki/Authority-Ledger-Binding) | Ledger format, chaining, revocation, time-windowed authority |

### Related Canonical Mermaid Diagrams

| # | Diagram | Path |
|---|---------|------|
| 11 | [Seal-and-Prove Pipeline](../enterprise/docs/mermaid/11-seal-and-prove.md) | Admissibility chain |
| 16 | [Authority Boundary Primitive](../enterprise/docs/mermaid/16-authority-boundary-primitive.md) | ABP lifecycle + composition |
| 17 | [EDGE System](../enterprise/docs/mermaid/17-edge-system.md) | Module map, gate flow, delegation loop |
