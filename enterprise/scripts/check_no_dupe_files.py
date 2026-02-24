#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BAD_PATTERNS = [
    re.compile(r".*\s2(?:\.[^/]+)?$", re.IGNORECASE),
    re.compile(r".*\s\(\d+\)(?:\.[^/]+)?$", re.IGNORECASE),
    re.compile(r".*\scopy(?:\.[^/]+)?$", re.IGNORECASE),
]

ALLOWLIST = {
    # Add explicit exceptions here only when intentional.
}


def git_list_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        text=False,
    )
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def is_bad(path: str) -> bool:
    if path in ALLOWLIST:
        return False
    name = Path(path).name
    return any(p.match(name) for p in BAD_PATTERNS)


def main() -> int:
    try:
        files = git_list_files()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: failed to list files via git: {exc}", file=sys.stderr)
        return 2

    offenders = sorted(p for p in files if is_bad(p))
    if offenders:
        print("Duplicate-like filenames detected:")
        for item in offenders:
            print(f"- {item}")
        print("\nRename/remove these files before committing.")
        return 1

    print("No duplicate-like filenames found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
