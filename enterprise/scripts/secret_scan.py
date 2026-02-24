#!/usr/bin/env python3
import pathlib
import re
import sys

pat = re.compile(r'(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36,}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----)')
binary_ext = {'.png','.jpg','.jpeg','.gif','.zip','.pdf','.ico','.woff','.woff2','.ttf','.eot'}
hits = []
for p in pathlib.Path('.').rglob('*'):
    if p.is_dir():
        continue
    if '.git' in p.parts:
        continue
    if p.suffix.lower() in binary_ext:
        continue
    try:
        s = p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    if pat.search(s):
        hits.append(str(p))

if hits:
    print('FAIL: secret-like patterns detected in:')
    for h in hits:
        print(' -', h)
    raise SystemExit(1)

print('PASS: no obvious secret patterns')
