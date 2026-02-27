#!/usr/bin/env python3

"""
Canonical execution entrypoint.
Default deny: no run proceeds without passing pre_exec_gate.
"""

import subprocess
import sys


def main(argv: list[str]) -> int:
    gate = subprocess.run([sys.executable, "enterprise/scripts/pre_exec_gate.py", *argv[1:]])
    if gate.returncode != 0:
        print("FAIL: execution blocked by pre_exec_gate")
        return gate.returncode

    proc = subprocess.run([sys.executable, "enterprise/scripts/kpi_run.py", *argv[1:]])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
