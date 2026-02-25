#!/usr/bin/env python3
"""Edition guard: CORE must never import ENTERPRISE.

Scans every .py file under src/core/ for:
  - from enterprise ...
  - import enterprise ...
  - deepsigma_enterprise references
Reports file:line for each violation.
"""
import pathlib
import re
import sys

ENTERPRISE_PATTERNS = [
    re.compile(r'^\s*(from|import)\s+enterprise\b'),
    re.compile(r'\bdeepsigma_enterprise\b'),
]

violations = []

for p in pathlib.Path('src/core').rglob('*.py'):
    for lineno, line in enumerate(
        p.read_text(encoding='utf-8', errors='ignore').splitlines(),
        start=1,
    ):
        for pat in ENTERPRISE_PATTERNS:
            if pat.search(line):
                violations.append(f'  {p}:{lineno}  {line.strip()}')
                break  # one hit per line is enough

if violations:
    print('FAIL: CORE references ENTERPRISE:')
    for v in violations:
        print(v)
    raise SystemExit(1)

print('PASS: No enterprise imports in CORE')
