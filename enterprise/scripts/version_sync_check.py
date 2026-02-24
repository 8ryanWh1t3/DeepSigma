#!/usr/bin/env python3
import pathlib
import re
import sys

py = pathlib.Path('pyproject.toml').read_text(encoding='utf-8')
m = re.search(r'^version\s*=\s*"([^"]+)"', py, re.M)
if not m:
    print('FAIL: pyproject version not found')
    raise SystemExit(1)

py_v = m.group(1)
vfile = pathlib.Path('enterprise/release_kpis/VERSION.txt')
if not vfile.exists():
    print('FAIL: enterprise/release_kpis/VERSION.txt missing')
    raise SystemExit(1)

raw = vfile.read_text(encoding='utf-8').strip()
txt_v = raw[1:] if raw.startswith('v') else raw
if txt_v != py_v:
    print(f'FAIL: VERSION mismatch pyproject={py_v} version_txt={raw}')
    raise SystemExit(1)

print(f'PASS: version sync ({py_v})')
