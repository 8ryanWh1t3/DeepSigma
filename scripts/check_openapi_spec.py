#!/usr/bin/env python3
"""Validate exported OpenAPI spec coverage and operation metadata."""

from __future__ import annotations

import json
from pathlib import Path

REQUIRED_PATHS = [
    "/api/credibility/snapshot",
    "/mesh/{tenant_id}/summary",
    "/api/tenants",
    "/api/{tenant_id}/policy",
    "/api/{tenant_id}/audit/recent",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    spec_path = root / "docs" / "api" / "openapi.json"
    if not spec_path.exists():
        raise SystemExit(f"Missing spec: {spec_path}")

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    paths = spec.get("paths", {})
    failures: list[str] = []

    for path in REQUIRED_PATHS:
        if path not in paths:
            failures.append(f"Missing required path: {path}")

    for path, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        for method, op in operations.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(op, dict):
                failures.append(f"{method.upper()} {path}: operation must be object")
                continue
            if not op.get("summary"):
                failures.append(f"{method.upper()} {path}: missing summary")
            if not op.get("description"):
                failures.append(f"{method.upper()} {path}: missing description")

    if failures:
        print("OpenAPI validation FAILED:")
        for f in failures:
            print(f"- {f}")
        raise SystemExit(1)

    print("OpenAPI validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
