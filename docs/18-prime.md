# 18 — PRIME Threshold Gate

> Converting LLM probability gradients into decision-grade actions.

## What Is PRIME?

PRIME is the orchestration layer that sits between context assembly and action
execution in the Coherence Ops pipeline. It evaluates every proposed action
through three invariant lenses — **Truth**, **Reasoning**, and **Memory** —
and emits one of three verdicts:

| Verdict     | Meaning                                    | Action                    |
|-------------|--------------------------------------------|---------------------------|
| **APPROVE** | All invariants pass, composite score >= 0.7 | Execute the action        |
| **DEFER**   | Partial pass, score 0.4-0.7, or soft triggers | Queue for human review  |
| **ESCALATE**| Hard triggers fired or score < 0.4          | Immediate human attention |

PRIME ensures that no action enters execution without a traceable decision
lineage. Every verdict is recorded with full provenance — what scores were
computed, which triggers fired, and what configuration was active.

## How PRIME Relates to the Four Pillars

PRIME does not replace DLR, RS, DS, or MG. It orchestrates them:

```
DLR (Decision Ledger Registry)  ──┐
RS  (Record Store)               ──┤──> Context Assembly ──> PRIME Gate ──> Action
DS  (Drift Scanner)              ──┤
MG  (Memory Graph)               ──┘
```

- **DLR** provides the decision history that feeds PRIME's Memory invariant
- **RS** provides structured records that feed the Truth invariant
- **DS** provides drift signals that influence the temperature input
- **MG** provides the institutional memory and seal lineage

## The Three Invariants

### Truth (40% weight)

The Truth invariant validates the claim-evidence-source chain:

- **Claim**: What is being asserted?
- **Evidence**: What supports the claim?
- **Sources**: Where did the evidence come from?
- **Confidence Band**: HIGH / MODERATE / LOW / CONTESTED
- **Disconfirmers**: Active counter-evidence

Scoring:
- HIGH confidence base: 0.9
- MODERATE confidence base: 0.6
- LOW confidence base: 0.3
- CONTESTED confidence base: 0.2
- Evidence ratio bonus: up to +0.1

### Reasoning (30% weight)

The Reasoning invariant separates facts from interpretation:

- **Facts**: Verified, objective statements
- **Interpretations**: Subjective analysis built on facts
- **Assumptions**: Stated with explicit expiry timestamps (TTL)

The fact ratio (facts / total) forms the base score. A penalty of 0.1 per
assumption beyond 3 active ones prevents assumption accumulation.

Expired assumptions (past their TTL) are tracked separately and can trigger
escalation if they exceed the configured maximum.

### Memory (15% weight)

The Memory invariant validates decision lineage:

- **Seal ID**: Cryptographic seal on the decision record
- **Version**: How many patches have been applied
- **Lineage**: Hash chain of all patches
- **Patches**: Individual modifications with timestamps

Scoring rewards the presence of seals (+0.2), lineage depth (+0.05 per entry,
max +0.2), and version history (+0.1 for version > 1).

## Configuration

PRIME is configured via `PRIMEConfig`:

```python
from coherence_ops.prime import PRIMEConfig, PRIMEGate

config = PRIMEConfig(
    approve_threshold=0.7,       # Min composite for APPROVE
    defer_threshold=0.4,         # Min composite for DEFER
    min_evidence_ratio=0.5,      # Minimum evidence vs disconfirmers
    min_fact_ratio=0.3,          # Minimum facts vs interpretations
    max_expired_assumptions=2,   # Max before escalation trigger
    temperature_ceiling=0.8,     # System temp ceiling
    require_seal=False,          # Require memory seal?
    contested_claim_policy="defer",  # "defer" or "escalate"
)

gate = PRIMEGate(config)
```

See `specs/prime_gate.schema.json` for the full JSON Schema.

## Hard Escalation Triggers

These bypass the composite score and force an ESCALATE verdict:

1. **Temperature breach** — System temperature exceeds `temperature_ceiling`
2. **Missing seal** — `require_seal=True` but no seal present
3. **Contested escalation** — Active disconfirmers + `contested_claim_policy="escalate"`
4. **Expired assumptions** — More expired assumptions than `max_expired_assumptions`

## Usage Example

```python
from coherence_ops.prime import (
    PRIMEGate, PRIMEContext, PRIMEConfig,
    TruthInvariant, ReasoningInvariant, MemoryInvariant,
    ConfidenceBand,
)

# Create context from pipeline data
context = PRIMEContext(
    truth=TruthInvariant(
        claim="Policy P-101 conflicts with Program PRG-042",
        evidence=["Budget overlap detected", "Timeline collision in Q3"],
        sources=["portfolio_scanner_v2", "drift_report_2024-Q3"],
        confidence=ConfidenceBand.HIGH,
    ),
    reasoning=ReasoningInvariant(
        facts=["P-101 allocates 2M to cloud migration",
               "PRG-042 requires on-prem infrastructure"],
        interpretations=["These programs cannot coexist without resequencing"],
        assumptions=[{
            "text": "Cloud migration timeline holds",
            "expires_at": 1735689600,
        }],
    ),
    memory=MemoryInvariant(
        seal_id="seal_abc123",
        version=3,
        lineage=["a1b2c3", "d4e5f6", "g7h8i9"],
    ),
    coherence_score=0.82,
    temperature=0.35,
)

# Run the gate
gate = PRIMEGate()
verdict = gate.evaluate(context)

print(verdict.verdict)          # Verdict.APPROVE
print(verdict.composite_score)  # ~0.79
print(verdict.reasoning)        # Full reasoning string
print(verdict.lineage)          # Decision provenance
```

## Pipeline Integration

PRIME integrates with `run_supervised` as a middleware step:

```
Episode Start
  -> Context Assembly (DLR + RS + DS + MG)
  -> PRIME Gate evaluation
  -> If APPROVE: execute action
  -> If DEFER: queue for review, continue episode
  -> If ESCALATE: halt, notify, record
  -> Episode Record (includes PRIME verdict)
Episode End
```

The PRIME verdict is stored in the episode record for full traceability.

## Files

| File | Purpose |
|------|---------|
| `coherence_ops/prime.py` | Core implementation |
| `specs/prime_gate.schema.json` | JSON Schema for inputs/outputs |
| `tests/test_prime.py` | Unit tests |
| `archive/mermaid/27-prime-threshold-gate.md` | Visual diagrams (archived) |

## Related Concepts

- **CTI (Coherence Threat Index)** — PRIME's composite score feeds into CTI
- **DAT (Dynamic Assertion Testing)** — Tests assertions that PRIME evaluates
- **DDR (Deep Dive Review)** — Triggered when PRIME escalates repeatedly
- **Temperature** — System-level metric that influences PRIME's ceiling checks
- **IRIS** — The operator interface that queries PRIME verdicts
