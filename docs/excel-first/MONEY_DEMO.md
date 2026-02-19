---
title: "Excel-first Money Demo"
version: "0.6.3"
date: "2026-02-19"
---

# Excel-first Money Demo

> One command. Deterministic Drift→Patch proof — no LLM, no network.

---

## What It Proves

The Money Demo generates a governed workbook, validates its BOOT contract, simulates a real scenario (expired assumption), detects drift, proposes a patch, and computes a coherence delta — all in one deterministic command.

This proves the full Excel-first governance loop end-to-end:

```
Generate → Validate → Run → Drift → Patch → Delta
```

---

## Run It

```bash
# Module invocation
python -m demos.excel_first --out out/excel_money_demo

# Or via console entry point (after pip install -e .)
excel-demo --out out/excel_money_demo
```

---

## Expected Output

```
out/excel_money_demo/
  workbook.xlsx          Governed workbook (BOOT + 7 named tables)
  run_record.json        Scenario: ASM-005 TTL expired
  drift_signal.json      Drift detected (freshness, HIGH severity)
  patch_stub.json        Proposed fix (refresh assumption)
  coherence_delta.txt    Before/after coherence scores
```

---

## What Each Artifact Contains

### `run_record.json`

Simulates scanning the workbook and finding assumption ASM-005 has expired:
- `ttl_expired: true`
- `days_since_validation: 42` (half-life was 21 days)
- `current_confidence: 0.35` (decayed from 0.80)

### `drift_signal.json`

Drift event emitted when TTL expiry is detected:
- `drift_detected: true`
- `drift_type: "freshness"`
- `severity: "HIGH"`
- `recommended_patch_type: "RETCON"`

### `patch_stub.json`

Corrective action to restore coherence:
- Refresh ASM-005 with current data
- Restore confidence to 0.75
- Update status to REFRESHED

### `coherence_delta.txt`

Before/after scoring:
- `before_score` — based on field coverage, canon compliance, current confidence
- `after_score` — same formula with patched confidence
- Positive delta confirms the patch improved coherence

---

## How It Maps to Coherence Ops

| Demo Step | Coherence Ops Primitive |
|-----------|------------------------|
| Generate | Decision Scaffold (DS) — workbook structure |
| Validate | BOOT Contract — CI gate |
| Run | Reasoning Scaffold (RS) — assumption scan |
| Drift | Drift Signal — freshness TTL expiry |
| Patch | Patch Packet — corrective action |
| Delta | Coherence Score — before/after measurement |

---

## See Also

- [Workbook Boot Protocol](WORKBOOK_BOOT_PROTOCOL.md) — BOOT!A1 spec + validation gate
- [Table Schemas](TABLE_SCHEMAS.md) — governance table definitions
- [Creative Director Suite](../../templates/creative_director_suite/README.md) — template workbook
