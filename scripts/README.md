# Pilot Scripts

## `compute_ci.py`

Computes a deterministic Coherence Index (CI) from markdown records in `pilot/`.

### Usage

```bash
python3 scripts/compute_ci.py
```

### Inputs

- `pilot/decisions/*.md`
- `pilot/assumptions/*.md`
- `pilot/drift/*.md`
- `pilot/patches/*.md`

### Outputs

- `pilot/reports/ci_report.json`
- `pilot/reports/ci_report.md`

### Scoring model (pilot)

Start at 100 and subtract:

- `-20` for each expired assumption not patched
- `-10` for each open drift signal
- `-5` for each decision missing Owner
- `-5` for each decision missing Seal
- `-5` if a decision has no linked assumptions
- `-5` if a drift signal has no linked patch
