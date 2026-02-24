#!/usr/bin/env python3
import pathlib
import re
import sys

bad = []
for p in pathlib.Path('src/core').rglob('*.py'):
    s = p.read_text(encoding='utf-8', errors='ignore')
    if re.search(r'\bdeepsigma_enterprise\b', s):
        bad.append(str(p))

if bad:
    print('FAIL: CORE references ENTERPRISE in:')
    for b in bad:
        print(' -', b)
    raise SystemExit(1)

print('PASS: No enterprise imports in CORE')
