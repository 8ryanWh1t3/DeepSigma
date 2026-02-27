#!/usr/bin/env python3
"""Generate Public Demo Pack — deterministic, reproducible admissibility pack.

Creates a complete admissibility pack with a publicly-known demo key so that
anyone can verify the full pipeline without credentials. The demo key is
intentionally public — it proves pipeline correctness, not secrecy.

Usage:
    python src/tools/reconstruct/generate_public_demo_pack.py
    python src/tools/reconstruct/generate_public_demo_pack.py --out-dir /tmp/demo-pack
"""
from __future__ import annotations

import argparse
import base64
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seal_and_prove import seal_and_prove  # noqa: E402
from transparency_log_head import write_head  # noqa: E402
from verify_pack import verify_pack  # noqa: E402

# ── Fixed Demo Constants ──────────────────────────────────────────
# This key is INTENTIONALLY PUBLIC. It demonstrates pipeline correctness.
DEMO_KEY_B64 = base64.b64encode(b"deepsigma-public-demo-key-2026!").decode()
DEMO_KEY_ID = "ds-demo-public-2026"
FIXED_CLOCK = "2026-02-21T00:00:00Z"
DEMO_DECISION_ID = "DEC-001"

DEFAULT_OUT_DIR = Path("enterprise/artifacts/public_demo_pack")
DEFAULT_DATA_DIR = Path("enterprise/artifacts/sample_data/prompt_os_v2")
DEFAULT_PROMPTS_DIR = Path("enterprise/prompts")
DEFAULT_SCHEMAS_DIR = Path("enterprise/schemas")
DEFAULT_POLICY_BASELINE = Path("enterprise/docs/governance/POLICY_BASELINE.md")
DEFAULT_POLICY_VERSION = Path("enterprise/docs/governance/POLICY_VERSION.txt")


def generate_demo_pack(
    out_dir: Path = DEFAULT_OUT_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
    prompts_dir: Path = DEFAULT_PROMPTS_DIR,
    schemas_dir: Path = DEFAULT_SCHEMAS_DIR,
    policy_baseline: Path = DEFAULT_POLICY_BASELINE,
    policy_version_file: Path = DEFAULT_POLICY_VERSION,
    demo_key: str = DEMO_KEY_B64,
) -> dict:
    """Generate a complete demo admissibility pack."""
    # Use a temp dir for intermediate outputs to avoid polluting artifacts/
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tmp_log = tmp_path / "log.ndjson"
        tmp_ledger = tmp_path / "ledger.ndjson"
        tmp_sealed_dir = tmp_path / "sealed"

        # Run the full seal-and-prove pipeline
        summary = seal_and_prove(
            decision_id=DEMO_DECISION_ID,
            clock=FIXED_CLOCK,
            sign_algo="hmac",
            sign_key_id=DEMO_KEY_ID,
            sign_key=demo_key,
            user="Demo-Operator",
            data_dir=data_dir,
            out_dir=tmp_sealed_dir,
            prompts_dir=prompts_dir,
            schemas_dir=schemas_dir,
            policy_baseline=policy_baseline,
            policy_version_file=policy_version_file,
            transparency_log=tmp_log,
            pack_dir=out_dir,
            auto_authority=True,
            authority_ledger=tmp_ledger,
            no_audit=False,
            no_replay_check=False,
        )

        # Generate log head
        write_head(tmp_log, out_dir / "LOG_HEAD.json")

    # Write README
    readme = (
        "# Public Demo Pack\n\n"
        "This pack was generated with a **publicly-known demo key** to demonstrate\n"
        "the full admissibility verification pipeline. The key is intentionally\n"
        "public — it proves pipeline correctness, not secrecy.\n\n"
        f"**Demo Key (base64):** `{demo_key}`\n\n"
        f"**Fixed Clock:** `{FIXED_CLOCK}`\n\n"
        f"**Decision:** `{DEMO_DECISION_ID}`\n\n"
        "## Verify\n\n"
        "```bash\n"
        f"python src/tools/reconstruct/verify_pack.py --pack {out_dir} --key \"{demo_key}\"\n"
        "```\n"
    )
    (out_dir / "README.md").write_text(readme)

    # Write verify instructions
    verify_instructions = (
        "# Verify This Pack\n\n"
        "```bash\n"
        f"python src/tools/reconstruct/verify_pack.py --pack {out_dir} --key \"{demo_key}\"\n"
        "```\n"
    )
    (out_dir / "VERIFY_INSTRUCTIONS.md").write_text(verify_instructions)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Public Demo Pack — reproducible admissibility demo"
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--demo-key", default=DEMO_KEY_B64,
                        help="Base64 demo key (default: built-in public key)")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--prompts-dir", type=Path, default=DEFAULT_PROMPTS_DIR)
    parser.add_argument("--schemas-dir", type=Path, default=DEFAULT_SCHEMAS_DIR)
    parser.add_argument("--policy-baseline", type=Path, default=DEFAULT_POLICY_BASELINE)
    parser.add_argument("--policy-version", type=Path, default=DEFAULT_POLICY_VERSION)
    args = parser.parse_args()

    # Clean output dir
    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary = generate_demo_pack(
        out_dir=args.out_dir,
        data_dir=args.data_dir,
        prompts_dir=args.prompts_dir,
        schemas_dir=args.schemas_dir,
        policy_baseline=args.policy_baseline,
        policy_version_file=args.policy_version,
        demo_key=args.demo_key,
    )

    # Self-verify
    vr = verify_pack(args.out_dir, key_b64=args.demo_key)

    print("=" * 60)
    print("  Public Demo Pack Generated")
    print("=" * 60)
    print(f"  Decision:     {summary['decision_id']}")
    print(f"  Run ID:       {summary['run_id']}")
    print(f"  Commit hash:  {summary['commit_hash']}")
    print(f"  Pack dir:     {args.out_dir}")
    print(f"  Demo key:     {args.demo_key}")
    print(f"  Self-verify:  {'PASS' if vr.passed else 'FAIL'} ({vr.total_checks} checks)")
    if summary.get("errors"):
        print(f"  Errors:       {summary['errors']}")
    print("=" * 60)

    return 0 if vr.passed else 1


if __name__ == "__main__":
    sys.exit(main())
