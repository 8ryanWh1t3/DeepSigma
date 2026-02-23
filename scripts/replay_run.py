#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
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


def replay(snapshot_path: Path, output_path: Path) -> None:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    input_path = Path(snapshot["input_path"])
    expected = snapshot["input_hash"]
    actual = sha256_file(input_path)
    if actual != expected:
        raise ValueError("snapshot input hash mismatch during replay")

    result = {"replay_status": "verified", "input_hash": actual}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def run_self_check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inp = root / "input.json"
        snap = root / "snapshot.json"
        out = root / "replay.json"
        inp.write_text('{"n":1}', encoding="utf-8")
        snap.write_text(
            json.dumps({"input_path": str(inp), "input_hash": sha256_file(inp)}),
            encoding="utf-8",
        )
        replay(snap, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        if data.get("replay_status") != "verified":
            return fail("replay output is not verified")

        bad = root / "snapshot_bad.json"
        bad.write_text(
            json.dumps({"input_path": str(inp), "input_hash": "0" * 64}),
            encoding="utf-8",
        )
        try:
            replay(bad, out)
            return fail("replay should fail on hash mismatch")
        except ValueError:
            pass
    print("PASS: replay self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay run from sealed snapshot")
    parser.add_argument("--snapshot", default="artifacts/run_snapshot.json")
    parser.add_argument("--output", default="artifacts/replay_result.json")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    try:
        replay(Path(args.snapshot), Path(args.output))
    except Exception as exc:
        return fail(str(exc))

    print("PASS: replay completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
