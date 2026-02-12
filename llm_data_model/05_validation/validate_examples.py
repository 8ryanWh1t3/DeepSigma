#!/usr/bin/env python3
"""
validate_examples.py — One-command demo for the LLM Data Model.

Validates every JSON example in 03_examples/ against the canonical
record schema, prints a sample retrieval query, and exits 0 on success.

Usage:
    python llm_data_model/05_validation/validate_examples.py
"""

import json
import os
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    """Load and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_envelope(record: dict, filename: str) -> list:
    """Validate a record against the canonical envelope rules.

    Returns a list of error strings (empty = valid).
    This is a lightweight structural validator that does not
    require jsonschema as a dependency.
    """
    errors = []
    required_fields = [
        "record_id", "record_type", "created_at", "observed_at",
        "source", "provenance", "confidence", "ttl", "labels",
        "links", "content", "seal",
    ]

    # Check required top-level fields
    for field in required_fields:
        if field not in record:
            errors.append(f"  [{filename}] Missing required field: {field}")

    # Validate record_id format
    rid = record.get("record_id", "")
    if not rid.startswith("rec_"):
        errors.append(f"  [{filename}] record_id must start with rec_: {rid}")

    # Validate record_type enum
    valid_types = {"Claim", "DecisionEpisode", "Event", "Document", "Entity", "Metric"}
    rtype = record.get("record_type", "")
    if rtype not in valid_types:
        errors.append(f"  [{filename}] Invalid record_type: {rtype}")

    # Validate source block
    source = record.get("source", {})
    if "system" not in source:
        errors.append(f"  [{filename}] source.system is required")

    # Validate provenance chain
    prov = record.get("provenance", {})
    chain = prov.get("chain", [])
    if len(chain) < 1:
        errors.append(f"  [{filename}] provenance.chain must have at least 1 entry")
    for i, step in enumerate(chain):
        if "type" not in step:
            errors.append(f"  [{filename}] provenance.chain[{i}] missing type")
        elif step["type"] not in {"claim", "evidence", "source"}:
            errors.append(
                f"  [{filename}] provenance.chain[{i}] invalid type: {step['type']}"
            )

    # Validate confidence
    conf = record.get("confidence", {})
    score = conf.get("score")
    if score is not None and not (0 <= score <= 1):
        errors.append(f"  [{filename}] confidence.score must be 0-1: {score}")
    if "explanation" not in conf:
        errors.append(f"  [{filename}] confidence.explanation is required")

    # Validate TTL
    ttl = record.get("ttl")
    if ttl is not None and ttl < 0:
        errors.append(f"  [{filename}] ttl must be >= 0: {ttl}")

    # Validate labels
    labels = record.get("labels", {})
    if "domain" not in labels:
        errors.append(f"  [{filename}] labels.domain is required")

    # Validate seal
    seal = record.get("seal", {})
    for sf in ["hash", "sealed_at", "version"]:
        if sf not in seal:
            errors.append(f"  [{filename}] seal.{sf} is required")

    return errors


def print_sample_query() -> None:
    """Print a sample retrieval query demonstrating the data model."""
    print()
    print("=" * 60)
    print("SAMPLE RETRIEVAL QUERY")
    print("=" * 60)
    query = {
        "description": "Find all claims supporting entity ACC-9921 with confidence > 0.8, not yet expired",
        "vector_search": {
            "query": "anomalous transfer pattern account takeover",
            "field": "content",
            "top_k": 10,
        },
        "filters": {
            "record_type": "Claim",
            "confidence.score": {"$gte": 0.8},
            "labels.domain": "fraud",
            "ttl_check": {"observed_at_plus_ttl": {"$gte": "now()"}},
        },
        "graph_expand": {
            "links.rel": "supports",
            "links.target": "rec_3nt1ty01-aaaa-4bbb-8ccc-ddddeeee0005",
            "depth": 2,
        },
        "return_fields": [
            "record_id",
            "confidence",
            "provenance.chain",
            "content",
            "seal.sealed_at",
        ],
    }
    print(json.dumps(query, indent=2))
    print()


def main() -> int:
    """Run validation and print results."""
    # Resolve paths relative to this script
    script_dir = Path(__file__).resolve().parent
    model_dir = script_dir.parent
    examples_dir = model_dir / "03_examples"

    print("LLM Data Model — Validation Report")
    print("=" * 60)
    print()

    if not examples_dir.exists():
        print(f"ERROR: Examples directory not found: {examples_dir}")
        return 1

    example_files = sorted(examples_dir.glob("*.json"))
    if not example_files:
        print(f"ERROR: No JSON files found in {examples_dir}")
        return 1

    all_errors: list = []
    for fpath in example_files:
        try:
            record = load_json(fpath)
        except json.JSONDecodeError as exc:
            all_errors.append(f"  [{fpath.name}] Invalid JSON: {exc}")
            continue

        errors = validate_envelope(record, fpath.name)
        if errors:
            all_errors.extend(errors)
            print(f"  FAIL  {fpath.name} ({len(errors)} error(s))")
        else:
            rtype = record.get("record_type", "?")
            conf = record.get("confidence", {}).get("score", "?")
            print(f"  PASS  {fpath.name}  [type={rtype}, confidence={conf}]")

    print()
    print(f"Files checked: {len(example_files)}")

    if all_errors:
        print(f"Errors found:  {len(all_errors)}")
        print()
        for err in all_errors:
            print(err)
        print()
        print("VALIDATION FAILED")
        return 1

    print("Errors found:  0")
    print()
    print("ALL EXAMPLES VALID")

    # Print sample query
    print_sample_query()

    return 0


if __name__ == "__main__":
    sys.exit(main())
