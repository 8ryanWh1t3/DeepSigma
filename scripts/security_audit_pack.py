#!/usr/bin/env python3
"""Build a shareable DISR security audit pack from repository artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_commit(root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return "unknown"


def _release_version(root: Path) -> str:
    version_file = root / "release_kpis" / "VERSION.txt"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "unknown"


def _copy_source(root: Path, out_dir: Path, rel_path: str) -> dict[str, Any]:
    src = root / rel_path
    if not src.exists():
        return {
            "source": rel_path,
            "status": "missing",
        }
    dest = out_dir / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {
        "source": rel_path,
        "status": "included",
        "output": str(dest.relative_to(out_dir)),
        "size_bytes": src.stat().st_size,
    }


def build_security_audit_pack(root: Path, out_dir: Path, *, strict: bool = False) -> dict[str, Any]:
    sources = [
        "data/security/security_events.jsonl",
        "data/security/authority_ledger.json",
        "artifacts/disr_demo/security_events.jsonl",
        "artifacts/disr_demo/authority_ledger.json",
        "artifacts/disr_demo/disr_demo_summary.json",
        "release_kpis/SECURITY_GATE_REPORT.md",
        "release_kpis/SECURITY_GATE_REPORT.json",
        "release_kpis/security_metrics.json",
        "release_kpis/scalability_metrics.json",
        "release_kpis/benchmark_history.json",
        "governance/security_crypto_policy.json",
        "schemas/core/security_crypto_policy.schema.json",
        "schemas/core/crypto_envelope.schema.json",
        "docs/docs/security/DISR.md",
        "docs/docs/security/KEY_LIFECYCLE.md",
        "docs/docs/security/RECOVERY_RUNBOOK.md",
        "docs/docs/security/ENVELOPE_VERSIONING.md",
    ]

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    items = [_copy_source(root, out_dir, rel_path) for rel_path in sources]
    missing = [item for item in items if item["status"] == "missing"]
    included = [item for item in items if item["status"] == "included"]

    versions = {
        "generated_at": _utc_now_iso(),
        "git_commit": _git_commit(root),
        "release_version": _release_version(root),
    }
    (out_dir / "versions.json").write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "1.0",
        "artifact": "security_audit_pack",
        "created_at": versions["generated_at"],
        "root": str(root),
        "counts": {
            "included": len(included),
            "missing": len(missing),
        },
        "files": items,
        "versions": versions,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if strict and missing:
        missing_paths = ", ".join(item["source"] for item in missing)
        raise RuntimeError(f"Missing required audit pack sources: {missing_paths}")

    return manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build security_audit_pack from DISR artifacts")
    parser.add_argument("--out-dir", default="security_audit_pack", help="Output directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any expected source artifact is missing",
    )
    args = parser.parse_args()

    out_dir = (ROOT / args.out_dir).resolve()
    manifest = build_security_audit_pack(ROOT, out_dir, strict=args.strict)
    print(json.dumps(manifest["counts"], indent=2))
    print(f"Wrote: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
