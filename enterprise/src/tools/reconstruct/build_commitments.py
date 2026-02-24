#!/usr/bin/env python3
"""Build Merkle commitment roots for governance input categories.

Computes four commitment roots (inputs, prompts, schemas, policies)
without exposing raw data — only sha256 hashes and the Merkle root.

Usage:
    python src/tools/reconstruct/build_commitments.py \\
        --data-dir artifacts/sample_data/prompt_os_v2 \\
        --prompts-dir prompts \\
        --schemas-dir schemas \\
        --policy-baseline docs/governance/POLICY_BASELINE.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from deterministic_io import list_files_deterministic
from merkle import merkle_root
from seal_bundle import hash_prompt_files, hash_schema_files, sha256_file


def build_commitment(
    data_dir: Path,
    prompts_dir: Path,
    schemas_dir: Path,
    policy_baseline: Path,
) -> dict:
    """Build commitment roots for all input categories.

    Returns dict with inputs_root, prompts_root, schemas_root, policies_root,
    leaf_count, and algorithm.
    """
    # Inputs (CSVs)
    input_hashes: list[str] = []
    for csv_file in list_files_deterministic(data_dir, "*.csv"):
        input_hashes.append(sha256_file(csv_file))

    # Prompts
    prompt_hash_map = hash_prompt_files(prompts_dir)
    prompt_hashes = [h for _, h in sorted(prompt_hash_map.items())]

    # Schemas
    schema_hash_map = hash_schema_files(schemas_dir)
    schema_hashes = [h for _, h in sorted(schema_hash_map.items())]

    # Policies
    policy_hashes: list[str] = []
    if policy_baseline.exists():
        policy_hashes.append(sha256_file(policy_baseline))

    total_leaves = (
        len(input_hashes) + len(prompt_hashes)
        + len(schema_hashes) + len(policy_hashes)
    )

    return {
        "inputs_root": merkle_root(input_hashes),
        "prompts_root": merkle_root(prompt_hashes),
        "schemas_root": merkle_root(schema_hashes),
        "policies_root": merkle_root(policy_hashes),
        "leaf_count": total_leaves,
        "algorithm": "sha256-merkle",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Merkle commitment roots")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--prompts-dir", type=Path, required=True)
    parser.add_argument("--schemas-dir", type=Path, required=True)
    parser.add_argument("--policy-baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None, help="Output JSON path")
    args = parser.parse_args()

    commitment = build_commitment(
        args.data_dir, args.prompts_dir, args.schemas_dir, args.policy_baseline,
    )

    output = json.dumps(commitment, indent=2, sort_keys=True)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output)
        print(f"Commitment roots written to: {args.out}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
