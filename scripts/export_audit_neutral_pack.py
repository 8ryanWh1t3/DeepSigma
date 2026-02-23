#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def export_pack(inputs: list[Path], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}
    for src in inputs:
        if not src.exists():
            raise FileNotFoundError(str(src))
        dst = output_dir / src.name
        shutil.copy2(src, dst)
        manifest[dst.name] = sha256_file(dst)

    manifest_path = output_dir / "MANIFEST.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        src1 = root / "decision.json"
        src2 = root / "authority.json"
        dst = root / "pack"
        src1.write_text('{"d":1}', encoding="utf-8")
        src2.write_text('{"a":1}', encoding="utf-8")
        manifest = export_pack([src1, src2], dst)
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if set(data.keys()) != {"decision.json", "authority.json"}:
            return fail("manifest keys mismatch")
    print("PASS: audit-neutral pack self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Export audit-neutral pack")
    parser.add_argument("--inputs", nargs="*", default=["artifacts/decision_record.json", "artifacts/action_contract.json"])
    parser.add_argument("--output-dir", default="artifacts/audit_neutral_pack")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        inputs = [Path(x) for x in args.inputs]
        manifest = export_pack(inputs, Path(args.output_dir))
    except Exception as exc:
        return fail(str(exc))

    print(f"PASS: audit-neutral pack exported ({manifest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
