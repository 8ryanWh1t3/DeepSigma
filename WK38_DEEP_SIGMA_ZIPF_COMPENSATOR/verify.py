#!/usr/bin/env python3
"""Run standard-library behavior tests and optional Node cross-language parity."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def first_difference(left, right, path="output"):
    if type(left) is not type(right):
        # JSON has one numeric type; avoid false failures for 1 versus 1.0.
        if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool) and left == right:
            return None
        return f"{path}: types differ"
    if isinstance(left, dict):
        if set(left) != set(right):
            return f"{path}: keys differ"
        for key in left:
            difference = first_difference(left[key], right[key], f"{path}.{key}")
            if difference:
                return difference
    elif isinstance(left, list):
        if len(left) != len(right):
            return f"{path}: lengths differ"
        for index, (a, b) in enumerate(zip(left, right)):
            difference = first_difference(a, b, f"{path}[{index}]")
            if difference:
                return difference
    elif left != right:
        return f"{path}: {left!r} != {right!r}"
    return None


def run_parity(node):
    from deep_sigma_zipf.engine import ValidationError, evaluate
    from tests.fixtures import invalid_scenarios, valid_scenarios

    scenarios = [(name, p, True) for name, p in valid_scenarios()]
    scenarios += [(name, p, False) for name, p in invalid_scenarios()]
    demo = ROOT / "data" / "demo.json"
    if demo.exists():
        scenarios.append(("packaged_demo", json.loads(demo.read_text(encoding="utf-8")), True))
    wire = [{"name": name, "payload": p} for name, p, _ in scenarios]
    completed = subprocess.run([node, str(ROOT / "tests" / "parity_runner.js")],
                               input=json.dumps(wire, allow_nan=False), text=True,
                               capture_output=True, cwd=ROOT, timeout=60)
    if completed.returncode:
        print("FAIL: JavaScript parity runner did not complete.", file=sys.stderr)
        print(completed.stderr.strip(), file=sys.stderr)
        return False
    actuals = json.loads(completed.stdout)
    if len(actuals) != len(scenarios):
        print("FAIL: JavaScript parity scenario count differs.", file=sys.stderr)
        return False
    failed = []
    for (name, p, should_accept), actual in zip(scenarios, actuals):
        try:
            expected = {"name": name, "accepted": True, "output": evaluate(p)}
        except ValidationError:
            expected = {"name": name, "accepted": False}
        if expected["accepted"] is not should_accept:
            failed.append(f"{name}: Python acceptance differs from fixture expectation")
        difference = first_difference(expected, actual)
        if difference:
            failed.append(f"{name}: {difference}")
    if failed:
        for failure in failed:
            print(f"FAIL parity: {failure}", file=sys.stderr)
        return False
    accepted = sum(1 for _, _, okay in scenarios if okay)
    print(f"PASS: Python/JavaScript parity for {len(scenarios)} scenarios ({accepted} valid, {len(scenarios) - accepted} rejected).", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-node", action="store_true", help="Fail when Node is unavailable.")
    args = parser.parse_args()
    print("Checking Python behavior...", flush=True)
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=ROOT)
    if tests.returncode:
        return tests.returncode
    print("PASS: Python behavior tests.", flush=True)
    node = shutil.which("node")
    if not node:
        if args.require_node:
            print("FAIL: Node is required but was not found.", file=sys.stderr)
            return 1
        print("SKIP: JavaScript parity requires Node; Python checks passed.", flush=True)
        return 0
    try:
        return 0 if run_parity(node) else 1
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: parity check could not run: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
