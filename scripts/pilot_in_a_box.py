#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilot"
ART = ROOT / "artifacts" / "sealed_runs"


def run_ci() -> int:
    out = subprocess.check_output([sys.executable, "scripts/compute_ci.py"], text=True, cwd=ROOT)
    for line in out.splitlines():
        if line.strip().startswith("CI score:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError("Could not parse CI score")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def snapshot(tag: str) -> Path:
    stamp = f"{date.today().isoformat()}_{tag}"
    dest = ART / stamp
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(PILOT, dest)
    return dest


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)

    snapshot("baseline_before")
    baseline = run_ci()

    expired = (date.today() - timedelta(days=1)).isoformat()
    a_id = "A-2026-069"
    write(
        PILOT / "assumptions" / f"{a_id}.md",
        f"""# Assumption

- Assumption ID: {a_id}
- Expiry date (YYYY-MM-DD): {expired}
- Description: Deterministic failure seed assumption for PASS->FAIL->PASS drill.
""",
    )

    d_id = "DRIFT-2026-069"
    write(
        PILOT / "drift" / f"{d_id}.md",
        f"""# Drift Signal

- Drift ID: {d_id}
- Status: Open
- Summary: Deterministic failure seed drift (no linked patch yet).
- Impact: Forces CI to demonstrate FAIL behavior.
""",
    )

    snapshot("after_fail_injected")
    fail_score = run_ci()

    p_id = "PATCH-2026-069"
    write(
        PILOT / "patches" / f"{p_id}.md",
        f"""# Patch

- Patch ID: {p_id}
- Date: {date.today().isoformat()}
- Linked Drift: {d_id}
- Patched Assumptions: {a_id}

## Change
- This patch closes the failure-seed drift and documents remediation.
""",
    )

    write(
        PILOT / "drift" / f"{d_id}.md",
        f"""# Drift Signal

- Drift ID: {d_id}
- Status: Closed
- Summary: Deterministic failure seed drift (patched).
- Patch Reference: {p_id}
""",
    )

    snapshot("after_patch_applied")
    pass_score = run_ci()

    print("")
    print("=== PILOT IN A BOX RESULTS ===")
    print(f"Baseline CI: {baseline}")
    print(f"After FAIL injection CI: {fail_score}")
    print(f"After PATCH remediation CI: {pass_score}")
    print("")
    print("Expected behavior:")
    print("- FAIL injection should push CI < 75 (hard fail).")
    print("- Patch remediation should restore CI >= 90 (pass).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
