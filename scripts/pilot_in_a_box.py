#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilot"
ART = ROOT / "artifacts" / "sealed_runs"


def run_ci() -> int:
    out = subprocess.check_output(["python", "scripts/compute_ci.py"], text=True)
    for line in out.splitlines():
        if line.strip().startswith("CI score:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError("Could not parse CI score from compute_ci.py output")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def snapshot(tag: str) -> None:
    stamp = f"{date.today().isoformat()}_{tag}"
    dest = ART / stamp
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(PILOT, dest)


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)

    snapshot("baseline_before")
    baseline = run_ci()

    # --- FAIL injection (deterministic) ---
    # Expired assumption (should trigger penalty in CI)
    expired = (date.today() - timedelta(days=1)).isoformat()
    a_id = "A-2026-071"
    write(PILOT / "assumptions" / f"{a_id}.md", f"""# Assumption

- Assumption ID: {a_id}
- Expiry date (YYYY-MM-DD): {expired}
- Description: Deterministic failure seed assumption for PASS→FAIL→PASS drill.
""")

    # Open drift without patch (should trigger penalty in CI)
    d_id = "DRIFT-2026-071"
    write(PILOT / "drift" / f"{d_id}.md", f"""# Drift Signal

- Drift ID: {d_id}
- Status: Open
- Summary: Deterministic failure seed drift (no linked patch yet).
- Impact: Forces CI to demonstrate FAIL behavior.
""")

    snapshot("after_fail_injected")
    fail_score = run_ci()

    # --- PATCH remediation (restore PASS) ---
    p_id = "PATCH-2026-071"
    write(PILOT / "patches" / f"{p_id}.md", f"""# Patch

- Patch ID: {p_id}
- Date: {date.today().isoformat()}
- Linked Drift: {d_id}
- Patched Assumptions: {a_id}

## Change
- Close drift and document remediation for the failure-seed assumption.
""")

    # Close drift + reference patch
    write(PILOT / "drift" / f"{d_id}.md", f"""# Drift Signal

- Drift ID: {d_id}
- Status: Closed
- Summary: Deterministic failure seed drift (patched).
- Patch Reference: {p_id}
""")

    snapshot("after_patch_applied")
    pass_score = run_ci()

    print("")
    print("=== PILOT IN A BOX RESULTS (Build 71) ===")
    print(f"Baseline CI: {baseline}")
    print(f"After FAIL injection CI: {fail_score}")
    print(f"After PATCH remediation CI: {pass_score}")
    print("")
    print("Target behavior:")
    print("- FAIL injection pushes CI below your failure threshold (ideally < 75).")
    print("- PATCH remediation restores CI above pass threshold (ideally ≥ 90).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
