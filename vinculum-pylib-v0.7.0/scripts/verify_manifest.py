from pathlib import Path
import hashlib
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()
entries = (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
failures = []
for row in entries:
    digest, relative = row.split("  ", 1)
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        failures.append(relative)
print(f"Verified {len(entries) - len(failures)}/{len(entries)} manifest entries")
for name in failures: print("FAILED:", name)
raise SystemExit(bool(failures))
