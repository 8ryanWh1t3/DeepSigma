#!/usr/bin/env python3
"""Generate deterministic DeepSigma Core baseline proof artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "docs" / "examples" / "demo-stack"
RUN_DIR = OUT_DIR / "drift_patch_cycle_run"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], env: dict[str, str]) -> dict[str, object]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    steps = [
        run([sys.executable, "-m", "core.examples.drift_patch_cycle"], env),
        run([sys.executable, "-m", "pytest", "tests/test_money_demo.py", "-q"], env),
    ]

    artifacts = {}
    for p in sorted(RUN_DIR.glob("*")):
        if p.is_file():
            artifacts[str(p.relative_to(ROOT))] = sha256_file(p)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(int(s["returncode"]) == 0 for s in steps) else "FAIL",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "commands": steps,
        "artifact_sha256": artifacts,
    }

    json_path = OUT_DIR / "CORE_BASELINE_REPORT.json"
    md_path = OUT_DIR / "CORE_BASELINE_REPORT.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# DeepSigma Core Baseline Report",
        "",
        f"- Status: **{report['status']}**",
        f"- Generated (UTC): {report['generated_at_utc']}",
        f"- Python: {report['python']}",
        f"- Platform: {report['platform']}",
        "",
        "## Commands",
    ]
    for idx, step in enumerate(steps, start=1):
        lines.append(f"{idx}. `{' '.join(step['cmd'])}` -> rc={step['returncode']}")

    lines.append("")
    lines.append("## Artifact Hashes")
    if artifacts:
        for path, digest in artifacts.items():
            lines.append(f"- `{path}`: `{digest}`")
    else:
        lines.append("- None")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"PASS: wrote {json_path.relative_to(ROOT)}")
    print(f"PASS: wrote {md_path.relative_to(ROOT)}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
