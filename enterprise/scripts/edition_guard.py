#!/usr/bin/env python3
"""Edition guard: CORE must never import ENTERPRISE.

Scans every .py file under src/core/ using AST parsing to detect imports
from any enterprise sub-package. Reports file:line for each violation.
"""
import ast
import pathlib
import sys

# All top-level package names that live under enterprise/src/
ENTERPRISE_PACKAGES = frozenset({
    "adapters",
    "credibility_engine",
    "deepsigma",
    "demos",
    "engine",
    "enterprise",
    "governance",
    "mdpt",
    "mesh",
    "services",
    "tenancy",
    "tools",
    "verifiers",
})

violations = []

for p in pathlib.Path("src/core").rglob("*.py"):
    source = p.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(source, filename=str(p))
    except SyntaxError:
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in ENTERPRISE_PACKAGES:
                    violations.append(
                        f"  {p}:{node.lineno}  import {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in ENTERPRISE_PACKAGES:
                    violations.append(
                        f"  {p}:{node.lineno}  from {node.module} import ..."
                    )

if violations:
    print("FAIL: CORE references ENTERPRISE packages:")
    for v in violations:
        print(v)
    raise SystemExit(1)

print("PASS: No enterprise imports in CORE")
