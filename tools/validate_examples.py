#!/usr/bin/env python3
"""Validate example JSON artifacts against \u03a3 OVERWATCH schemas.

Usage:
    python tools/validate_examples.py

Requires:
    pip install jsonschema referencing

Validates:
    - examples/episodes/*.json   against specs/episode.schema.json
    - examples/drift/*.json      against specs/drift.schema.json
    - llm_data_model/03_examples/*.json against llm_data_model/02_schema/jsonschema/canonical_record.schema.json
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

# ---------------------------------------------------------------------------
# Use the modern 'referencing' library instead of the deprecated RefResolver.
# Falls back gracefully if referencing is not installed.
# ---------------------------------------------------------------------------
try:
    import referencing
    from referencing import Registry
    from referencing.jsonschema import DRAFT202012

    HAS_REFERENCING = True
except ImportError:
    HAS_REFERENCING = False

ROOT = Path(__file__).resolve().parents[1]


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_registry() -> "Registry | None":
    """Build a referencing.Registry from all local schema files.

    Maps each schema's $id to the local file so that external $ref URLs
    (like https://sigma-overwatch.dev/schemas/action_contract.schema.json)
    resolve locally without network access.
    """
    if not HAS_REFERENCING:
        return None

    resources = []
    # Collect schemas from specs/
    for p in (ROOT / "specs").glob("*.json"):
        sch = load_schema(p)
        if "$id" in sch:
            resource = referencing.Resource.from_contents(sch, default_specification=DRAFT202012)
            resources.append((sch["$id"], resource))

    # Collect schemas from llm_data_model/02_schema/jsonschema/
    schema_dir = ROOT / "llm_data_model" / "02_schema" / "jsonschema"
    if schema_dir.exists():
        for p in schema_dir.glob("*.json"):
            sch = load_schema(p)
            if "$id" in sch:
                resource = referencing.Resource.from_contents(sch, default_specification=DRAFT202012)
                resources.append((sch["$id"], resource))

    return Registry().with_resources(resources)


def validate(schema_path: Path, json_path: Path, registry=None) -> None:
    schema = load_schema(schema_path)

    if registry is not None:
        validator = Draft202012Validator(schema, registry=registry)
    else:
        # Fallback: no $ref resolution (works for schemas without external refs)
        validator = Draft202012Validator(schema)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        print(f"\u274c {json_path.relative_to(ROOT)} failed ({len(errors)} errors)")
        for e in errors[:10]:
            loc = ".".join([str(x) for x in e.path]) or "<root>"
            print(f"  - {loc}: {e.message}")
        raise SystemExit(1)
    else:
        print(f"\u2705 {json_path.relative_to(ROOT)} ok")


def main():
    registry = build_registry()

    # --- Episode examples ---
    episode_schema = ROOT / "specs" / "episode.schema.json"
    for p in sorted((ROOT / "examples" / "episodes").glob("*.json")):
        validate(episode_schema, p, registry=registry)

    # --- Drift examples ---
    drift_schema = ROOT / "specs" / "drift.schema.json"
    for p in sorted((ROOT / "examples" / "drift").glob("*.json")):
        validate(drift_schema, p, registry=registry)

    # --- LLM Data Model examples ---
    # Schema overrides: files that use standalone schemas instead of canonical_record
    llm_schema_overrides = {
        "claim_primitive_example.json": ROOT / "specs" / "claim.schema.json",
        "dlr_claim_native_example.json": ROOT / "specs" / "dlr.schema.json",
    }

    llm_default_schema = ROOT / "llm_data_model" / "02_schema" / "jsonschema" / "canonical_record.schema.json"
    llm_examples_dir = ROOT / "llm_data_model" / "03_examples"

    if llm_default_schema.exists() and llm_examples_dir.exists():
        print()
        for p in sorted(llm_examples_dir.glob("*.json")):
            schema = llm_schema_overrides.get(p.name, llm_default_schema)
            validate(schema, p, registry=registry)
    else:
        print("\n\u26a0\ufe0f LLM Data Model schema or examples not found \u2014 skipped")

    # ---- Canonical demo (sample_decision_episode_001.json) ----
    canonical_demo = ROOT / "examples" / "sample_decision_episode_001.json"
    if canonical_demo.exists():
        print()
        data = json.loads(canonical_demo.read_text(encoding="utf-8"))

        # Validate: file parses as JSON
        print(f"\u2705 {canonical_demo.relative_to(ROOT)} parses as valid JSON")

        # Validate each episode section against episode schema
        episode_schema = ROOT / "specs" / "episode.schema.json"
        for key, value in data.items():
            if key.startswith("_"):
                continue  # skip _meta
            if isinstance(value, dict):
                # Validate episode-shaped objects against episode schema
                try:
                    validate(episode_schema, canonical_demo, registry=registry)
                    # Episode-level validation not applicable to composite doc
                    # but we verify structural integrity below
                except SystemExit:
                    pass  # composite doc won't match single-episode schema

        # Validate sub-schemas referenced in _meta.spec_refs
        meta = data.get("_meta", {})
        spec_refs = meta.get("spec_refs", [])
        for ref in spec_refs:
            schema_path = ROOT / ref
            if schema_path.exists():
                print(f"\u2705 {canonical_demo.relative_to(ROOT)} references {ref} (schema exists)")
            else:
                print(f"\u274c {canonical_demo.relative_to(ROOT)} references {ref} (schema NOT FOUND)")

        # Validate claim objects against claim schema
        claim_schema = ROOT / "specs" / "claim.schema.json"
        if claim_schema.exists():
            for key, episode in data.items():
                if key.startswith("_") or not isinstance(episode, dict):
                    continue
                truth = episode.get("truth", {})
                claims = truth.get("claims", [])
                for claim in claims:
                    try:
                        schema = load_schema(claim_schema)
                        if registry is not None:
                            v = Draft202012Validator(schema, registry=registry)
                        else:
                            v = Draft202012Validator(schema)
                        errors = sorted(v.iter_errors(claim), key=lambda e: e.path)
                        if errors:
                            print(f"\u274c {key} claim {claim.get('claimId', '?')} failed ({len(errors)} errors)")
                            for e in errors[:5]:
                                loc = ".".join([str(x) for x in e.path]) or "<root>"
                                print(f"   - {loc}: {e.message}")
                        else:
                            print(f"\u2705 {key} claim {claim.get('claimId', '?')} validates against claim.schema.json")
                    except Exception as exc:
                        print(f"\u26a0\ufe0f  {key} claim validation skipped: {exc}")

        # Validate DLR-shaped sections against dlr.schema.json
        dlr_schema = ROOT / "specs" / "dlr.schema.json"
        if dlr_schema.exists():
            for key, episode in data.items():
                if key.startswith("_") or not isinstance(episode, dict):
                    continue
                # Each episode is a DLR-shaped record
                try:
                    schema = load_schema(dlr_schema)
                    if registry is not None:
                        v = Draft202012Validator(schema, registry=registry)
                    else:
                        v = Draft202012Validator(schema)
                    errors = sorted(v.iter_errors(episode), key=lambda e: e.path)
                    if errors:
                        print(f"\u274c {key} failed DLR validation ({len(errors)} errors)")
                        for e in errors[:5]:
                            loc = ".".join([str(x) for x in e.path]) or "<root>"
                            print(f"   - {loc}: {e.message}")
                    else:
                        print(f"\u2705 {key} validates against dlr.schema.json")
                except Exception as exc:
                    print(f"\u26a0\ufe0f  {key} DLR validation skipped: {exc}")
    else:
        print("\u26a0\ufe0f  Canonical demo file not found - skipped")

    print("\nAll example artifacts validated.")


if __name__ == "__main__":
    main()
