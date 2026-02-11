#!/usr/bin/env python3
"""Validate example JSON artifacts against Σ OVERWATCH schemas.

Usage:
  python tools/validate_examples.py

Requires:
  pip install jsonschema pyyaml
"""

from __future__ import annotations

import json
from pathlib import Path
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[1]

def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def build_resolver() -> RefResolver:
    # Map schema $id URLs to local files
    store = {}
    for p in (ROOT / "specs").glob("*.json"):
        sch = load_schema(p)
        if "$id" in sch:
            store[sch["$id"]] = sch
    return RefResolver.from_schema(store.get("https://sigma-overwatch.dev/schemas/episode.schema.json", {}), store=store)

def validate(schema_path: Path, json_path: Path) -> None:
    schema = load_schema(schema_path)
    resolver = build_resolver()
    validator = Draft202012Validator(schema, resolver=resolver)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        print(f"❌ {json_path.relative_to(ROOT)} failed ({len(errors)} errors)")
        for e in errors[:10]:
            loc = ".".join([str(x) for x in e.path]) or "<root>"
            print(f"  - {loc}: {e.message}")
        raise SystemExit(1)
    else:
        print(f"✅ {json_path.relative_to(ROOT)} ok")

def main():
    episode_schema = ROOT / "specs" / "episode.schema.json"
    drift_schema = ROOT / "specs" / "drift.schema.json"

    for p in sorted((ROOT / "examples" / "episodes").glob("*.json")):
        validate(episode_schema, p)

    for p in sorted((ROOT / "examples" / "drift").glob("*.json")):
        validate(drift_schema, p)

    print("\nAll example artifacts validated.")

if __name__ == "__main__":
    main()
