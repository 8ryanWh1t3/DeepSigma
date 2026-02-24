# Prompt OS v2 — Scoring Documentation

Four scoring systems drive prioritization, credibility assessment, prompt governance, and assumption lifecycle management.

---

## 1. Decision PriorityScore

**Location:** `DECISION_LOG` → `PriorityScore` column
**Range:** ~0–8 (unbounded upper, typical max ~8)

Ranks decisions by urgency and structural risk.

### Components

| Factor | Weight | Description |
|--------|--------|-------------|
| **Blast Radius** (1–5) | × 0.3 | Higher blast radius → higher priority |
| **Irreversibility** (5 − Reversibility) | × 0.2 | Less reversible → higher priority |
| **Confidence Penalty** | × (1 − Confidence% × 0.1) | Lower confidence slightly reduces score (uncertainty discount) |
| **Cost of Delay** | +2 (High) / +1 (Medium) / +0 (Low) | Direct additive bonus for time-sensitive decisions |
| **Compression Risk** | +1.5 (High) / +0.75 (Medium) / +0 (Low) | Additive bonus when decision is being compressed (rushed without full reasoning) |

### Conceptual Formula

```
PriorityScore =
    (BlastRadius × 0.3 + (5 − Reversibility) × 0.2)
    × (1 − Confidence/100 × 0.1)
    + CostOfDelay_bonus
    + CompressionRisk_bonus
```

### Interpretation

| Score Range | Meaning |
|-------------|---------|
| 0–2 | Low priority — routine, reversible, low impact |
| 2–4 | Medium priority — some urgency or risk factors |
| 4–6 | High priority — significant blast radius or delay cost |
| 6+ | Critical — large blast radius, irreversible, time-sensitive |

---

## 2. Atomic Claims CredibilityScore

**Location:** `ATOMIC_CLAIMS` → `CredibilityScore` column
**Range:** 0–100

Scores truth claims based on evidence quality and freshness.

### Components

| Factor | Effect | Description |
|--------|--------|-------------|
| **Confidence Base** | Multiplicative | Claim confidence percentage (0–100) |
| **Evidence Bonus** | Multiplicative | EvidenceStrength / 100 applied to confidence |
| **Counter-Evidence Penalty** | Subtractive | CounterEvidence × 0.5 deducted |
| **Staleness Penalty** | Subtractive | StaleDays / 30, capped at 20 points |

### Conceptual Formula

```
CredibilityScore =
    CLAMP(0, 100,
        Confidence × (EvidenceStrength / 100)
        − CounterEvidence × 0.5
        − MIN(StaleDays / 30, 20)
    )
```

### Interpretation

| Score | Meaning |
|-------|---------|
| 80–100 | High credibility — strong evidence, recent, minimal counter-evidence |
| 60–79 | Moderate — usable but should be periodically re-verified |
| 40–59 | Low — significant counter-evidence or staleness; flag for review |
| 0–39 | Unreliable — do not use for decisions without fresh validation |

### Decay Behavior

Claims lose ~1 point per month from staleness alone. A claim with perfect evidence but no updates will cross the 60-threshold in approximately 18 months.

---

## 3. PromptHealth

**Location:** `PROMPT_LIBRARY` → `PromptHealth` column
**Range:** 0–100

Scores prompt assets by effectiveness and structural integrity.

### Components

| Factor | Weight | Description |
|--------|--------|-------------|
| **Success Rate** | × 0.5 | Percentage of successful uses contributes half the score |
| **Rating Bonus** | AvgRating × 10 | Quality rating scaled to 0–50 range |
| **Drift Penalty** | −20 (Major) / −10 (Minor) / −0 (None) | Structural drift degrades prompt health |

### Conceptual Formula

```
PromptHealth =
    CLAMP(0, 100,
        SuccessRate × 0.5
        + AvgRating × 10
        − DriftPenalty
    )
```

### Interpretation

| Score | Meaning |
|-------|---------|
| 80–100 | Healthy — performing well, no drift |
| 60–79 | Serviceable — minor issues, schedule review |
| 40–59 | Degraded — drift or low success rate; rewrite recommended |
| 0–39 | Critical — remove from active use; immediate rewrite |

### Drift Flags

| Flag | Trigger | Action |
|------|---------|--------|
| `None` | No structural changes detected | Continue use |
| `Minor` | Output format shift or edge-case failures | Schedule review |
| `Major` | Fundamental output misalignment | Immediate patch or decommission |

---

## 4. Assumption Half-Life + ExpiryRisk

**Location:** `ASSUMPTIONS` → `ExpiryDate` + `ExpiryRisk` columns

Models assumption validity as a time-decay function.

### Half-Life Model

Each assumption has a `HalfLife_days` value representing how long the assumption is expected to remain valid. The expiry date is computed as:

```
ExpiryDate = CreatedDate + HalfLife_days
```

This is a simplified model — in practice, assumptions don't decay linearly, but the half-life provides a useful review trigger.

### ExpiryRisk Color Logic

| Condition | Risk Level | Color | Action |
|-----------|-----------|-------|--------|
| ExpiryDate < TODAY() | Expired | **RED** | Immediate review; create patch if drift confirmed |
| ExpiryDate < TODAY() + 14 days | Approaching | **YELLOW** | Schedule review within the week |
| ExpiryDate ≥ TODAY() + 14 days | Valid | **GREEN** | No action needed |

### Lifecycle

1. **Create** — Assumption logged with confidence and half-life estimate
2. **Monitor** — ExpiryRisk color updates automatically each day
3. **YELLOW** — Review assumption; update confidence or extend half-life if re-validated
4. **RED** — Assumption expired; either validate (reset half-life) or create a `PATCH_LOG` entry
5. **Patch** — If assumption is invalidated, linked decisions should be re-evaluated

### Typical Half-Life Values

| Assumption Type | Typical Half-Life |
|-----------------|-------------------|
| Market conditions | 30–60 days |
| Budget approvals | 60–90 days |
| Technical architecture choices | 90–180 days |
| Regulatory requirements | 180–365 days |
| Vendor contracts | 365+ days |
