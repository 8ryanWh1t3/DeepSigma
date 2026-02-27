# Coherence Metrics

DeepSigma publishes four coherence metrics via `coherence metrics` and `coherence agent metrics`.

| Metric | Unit | Description |
|--------|------|-------------|
| `coherence_score` | score (0-100) | Overall coherence score across policy adherence, outcome health, drift control, and memory completeness. |
| `drift_density` | ratio | Drift signals per episode. Lower is better. |
| `authority_coverage` | ratio | Fraction of claims with a valid authority grant in the ledger. |
| `memory_coverage` | ratio | Fraction of DLR episodes represented in the Memory Graph. |

## CLI Usage

```bash
# Score a corpus
coherence metrics ./episodes --json

# Score an agent session
coherence agent metrics --session-dir ./agent --json

# With authority ledger
coherence metrics ./episodes --ledger ./authority_ledger.json --json
```

## Badge

The README badge reflects the latest CI coherence score:

```
[![Coherence Score](https://img.shields.io/badge/coherence-90%2F100-brightgreen)](./docs/metrics.md)
```
