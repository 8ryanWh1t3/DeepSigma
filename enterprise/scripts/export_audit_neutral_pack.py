#!/usr/bin/env python3

"""
Creates an audit-neutral proof pack:
- intent_packet.json
- input_snapshot.json
- authority_contract.json
- outputs_manifest.json
- proof_bundle.json
- ambiguity_policy.md
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 2


def export_pack(pack_dir: Path, files: list[Path]) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        if not path.exists():
            raise FileNotFoundError(f"missing required pack file: {path}")
        shutil.copy2(path, pack_dir / path.name)


def generate_proof() -> None:
    result = subprocess.run([sys.executable, "enterprise/scripts/crypto_proof.py"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError((result.stdout + "\n" + result.stderr).strip())


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runs = root / "runs"
        gov = root / "governance"
        pack = root / "packs" / "audit_neutral"
        runs.mkdir(parents=True)
        gov.mkdir(parents=True)
        (runs / "intent_packet.json").write_text('{"intent":"ok"}', encoding="utf-8")
        (runs / "input_snapshot.json").write_text('{"snapshot":"ok"}', encoding="utf-8")
        (runs / "authority_contract.json").write_text('{"authority":"ok"}', encoding="utf-8")
        (runs / "outputs_manifest.json").write_text('{"outputs":"ok"}', encoding="utf-8")
        (runs / "proof_bundle.json").write_text('{"intent_hash":"x","input_snapshot_hash":"y","authority_contract_hash":"z","outputs_hash":"w"}', encoding="utf-8")
        (gov / "ambiguity_policy.md").write_text("# policy", encoding="utf-8")

        export_pack(
            pack,
            [
                runs / "intent_packet.json",
                runs / "input_snapshot.json",
                runs / "authority_contract.json",
                runs / "outputs_manifest.json",
                runs / "proof_bundle.json",
                gov / "ambiguity_policy.md",
            ],
        )
        copied = {p.name for p in pack.iterdir()}
        expected = {
            "intent_packet.json",
            "input_snapshot.json",
            "authority_contract.json",
            "outputs_manifest.json",
            "proof_bundle.json",
            "ambiguity_policy.md",
        }
        if copied != expected:
            return fail("audit-neutral pack self-check copy set mismatch")

        try:
            export_pack(pack, [runs / "missing.json"])
            return fail("missing required file should fail pack export")
        except FileNotFoundError:
            pass

    print("PASS: audit-neutral pack self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Export audit-neutral proof pack")
    parser.add_argument("--pack-dir", default="packs/audit_neutral")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        generate_proof()
        files = [
            Path("runs/intent_packet.json"),
            Path("runs/input_snapshot.json"),
            Path("runs/authority_contract.json"),
            Path("runs/outputs_manifest.json"),
            Path("runs/proof_bundle.json"),
            Path("governance/ambiguity_policy.md"),
        ]
        export_pack(Path(args.pack_dir), files)
    except Exception as exc:
        return fail(str(exc))

    print(f"PASS: audit-neutral pack exported -> {args.pack_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
