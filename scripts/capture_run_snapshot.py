#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import tempfile
from datetime import datetime, timezone
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


def capture(input_path: Path, output_path: Path, provenance_path: Path | None) -> None:
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    snapshot = {
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_path": str(input_path),
        "input_hash": sha256_file(input_path),
        "env_fingerprint": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }

    if provenance_path:
        if not provenance_path.exists():
            raise FileNotFoundError(str(provenance_path))
        snapshot["provenance_path"] = str(provenance_path)
        snapshot["provenance_hash"] = sha256_file(provenance_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        input_path = root / "input.json"
        provenance_path = root / "prov.json"
        out = root / "snapshot.json"
        input_path.write_text('{"x":1}', encoding="utf-8")
        provenance_path.write_text('{"source":"fixture"}', encoding="utf-8")
        capture(input_path, out, provenance_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        if "input_hash" not in data or "env_fingerprint" not in data:
            return fail("snapshot missing required fields")
    print("PASS: snapshot self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture sealed run snapshot")
    parser.add_argument("--input", default="artifacts/input.json")
    parser.add_argument("--output", default="artifacts/run_snapshot.json")
    parser.add_argument("--provenance", default=None)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        provenance = Path(args.provenance) if args.provenance else None
        capture(Path(args.input), Path(args.output), provenance)
    except Exception as exc:
        return fail(str(exc))

    print("PASS: snapshot captured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
