# Before DeepSigma / After DeepSigma

## The Problem

AI agents make thousands of decisions. Without a reference layer, those decisions vanish.

## Without DeepSigma

| Aspect | Reality |
|--------|---------|
| **Decision Record** | Log line: `"Agent approved transfer"` |
| **Authority** | Implicit — who authorized this agent to act? |
| **Drift Detection** | None — behavior silently diverges over time |
| **Reconstruction** | "We think it did X, but we're not sure when or why" |
| **Audit** | Manual review of scattered logs, no coherence score |

## With DeepSigma

| Aspect | DeepSigma |
|--------|-----------|
| **Decision Record** | Sealed episode with 5-hash chain (intent, authority, snapshot, outputs, chain) |
| **Authority** | Authority slice with blessed claims, hash-bound at execution time |
| **Drift Detection** | 8 drift types (time, freshness, fallback, bypass, verify, outcome, fanout, contention), auto-fingerprinted |
| **Reconstruction** | `coherence iris query --type WHY --target ep-001` — sub-60-second provenance retrieval |
| **Audit** | 4-dimensional coherence score (0-100, grade A-F), deterministic every run |

## Proof

```bash
$ coherence demo
BASELINE   90.00 (A)
DRIFT      85.75 (B)   red=1
PATCH      90.00 (A)   patch=RETCON  drift_resolved=true
```

Three states. Same output every time. SHA-256 verified.

## Agent Integration

```bash
$ coherence agent log decision.json
Logged: ep-cli-0001  seal=sha256:eedab24c17173ca2...

$ coherence agent score
Score: 75.0/100  Grade: B
  Episodes: 1

$ coherence agent audit --json
{"passed": true, "summary": {"total_findings": 0, ...}}
```

Every decision sealed. Every drift detected. Every "why" answerable.
