# pyDOGE v0.1.0 Validation

## Scope

Executable MVP validation covers:

- mission and authority explanation
- orphan-work detection
- duplicate-work candidate detection
- dependency blast radius
- automation guardrails
- CERPA record order

## Required invariants

```text
NO EMPLOYEE SCORE
ORPHAN WORK → VALIDATE BEFORE AUTOMATE
WORKFORCE SIZING → LAST STEP
```

## Test command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Package smoke tests

```bash
pydoge analyze examples/agency.json
pydoge explain examples/agency.json W2
pydoge blast-radius examples/agency.json W1
python examples/demo.py
```
