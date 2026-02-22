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

    # --- CLEANUP (ensures deterministic behavior across repeated runs) ---
    seed_files = [
        PILOT / "assumptions" / "A-2026-071.md",
        PILOT / "assumptions" / "A-2026-072.md",
        PILOT / "drift" / "DRIFT-2026-071.md",
        PILOT / "drift" / "DRIFT-2026-072.md",
        PILOT / "patches" / "PATCH-2026-071.md",
        PILOT / "patches" / "PATCH-2026-072.md",
    ]
    for f in seed_files:
        if f.exists():
            f.unlink()

    snapshot("baseline_before")
    baseline = run_ci()

    # --- FAIL injection (deterministic + guaranteed to drop CI) ---
    expired = (date.today() - timedelta(days=1)).isoformat()

    assumptions = ["A-2026-071", "A-2026-072"]
    drifts = ["DRIFT-2026-071", "DRIFT-2026-072"]

    for a_id in assumptions:
        write(PILOT / "assumptions" / f"{a_id}.md", f"""# Assumption

- Assumption ID: {a_id}
- Expiry date (YYYY-MM-DD): {expired}
- Description: Deterministic failure seed assumption for PASS→FAIL→PASS drill.
""")

    for d_id in drifts:
        write(PILOT / "drift" / f"{d_id}.md", f"""# Drift Signal

- Drift ID: {d_id}
- Status: Open
- Summary: Deterministic failure seed drift (no linked patch yet).
- Impact: Forces CI to demonstrate FAIL behavior.
""")

    snapshot("after_fail_injected")
    fail_score = run_ci()

    # --- PATCH remediation (restore PASS) ---
    patches = ["PATCH-2026-071", "PATCH-2026-072"]

    # Patch #1 closes DRIFT-071 and references both assumptions
    write(PILOT / "patches" / f"{patches[0]}.md", f"""# Patch

- Patch ID: {patches[0]}
- Date: {date.today().isoformat()}
- Linked Drift: {drifts[0]}
- Patched Assumptions: {assumptions[0]}, {assumptions[1]}

## Change
- Close drift and document remediation for failure-seed assumptions.
""")

    write(PILOT / "drift" / f"{drifts[0]}.md", f"""# Drift Signal

- Drift ID: {drifts[0]}
- Status: Closed
- Summary: Deterministic failure seed drift (patched).
- Patch Reference: {patches[0]}
""")

    # Patch #2 closes DRIFT-072 and references both assumptions
    write(PILOT / "patches" / f"{patches[1]}.md", f"""# Patch

- Patch ID: {patches[1]}
- Date: {date.today().isoformat()}
- Linked Drift: {drifts[1]}
- Patched Assumptions: {assumptions[0]}, {assumptions[1]}

## Change
- Close drift and complete remediation for failure-seed assumptions.
""")

    write(PILOT / "drift" / f"{drifts[1]}.md", f"""# Drift Signal

- Drift ID: {drifts[1]}
- Status: Closed
- Summary: Deterministic failure seed drift (patched).
- Patch Reference: {patches[1]}
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
    print("- FAIL injection MUST push CI below the hard fail threshold (e.g., < 75).")
    print("- PATCH remediation MUST restore CI above pass threshold (e.g., ≥ 90).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
