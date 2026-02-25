#!/usr/bin/env python3
"""Verify Pack — one-command verification of an admissibility pack.

Auto-discovers files in a pack directory and runs all applicable checks:
  1. Replay sealed run (structural + hash + commitments)
  2. Signature verification (auto-detect single/multisig)
  3. Transparency log inclusion + chain integrity
  4. Authority ledger verification
  5. Determinism audit

Usage:
    python src/tools/reconstruct/verify_pack.py --pack /tmp/pack --key "$KEY"
    python src/tools/reconstruct/verify_pack.py --pack /tmp/pack --public-key "$PUB" --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from authority_ledger_verify import verify_ledger  # noqa: E402
from determinism_audit import audit_sealed_run  # noqa: E402
from verify_abp import verify_abp  # noqa: E402
from replay_sealed_run import replay  # noqa: E402
from transparency_log_append import verify_chain  # noqa: E402
from verify_signature import verify as verify_signature  # noqa: E402


class VerifyPackResult:
    """Accumulates verification results across all pack checks."""

    def __init__(self) -> None:
        self.sections: list[tuple[str, list[tuple[str, bool, str]]]] = []

    def add_section(self, name: str, checks: list[tuple[str, bool, str]]) -> None:
        self.sections.append((name, checks))

    @property
    def passed(self) -> bool:
        return all(ok for _, checks in self.sections for _, ok, _ in checks)

    @property
    def total_checks(self) -> int:
        return sum(len(checks) for _, checks in self.sections)

    @property
    def failed_count(self) -> int:
        return sum(1 for _, checks in self.sections for _, ok, _ in checks if not ok)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1


def _find_sealed(pack_dir: Path) -> Path | None:
    """Find the sealed run JSON in a pack directory."""
    candidates = sorted(pack_dir.glob("*.json"))
    for c in candidates:
        if c.name.endswith(".sig.json") or c.name.endswith(".manifest.json"):
            continue
        if c.name in ("transparency_log.ndjson", "authority_ledger.ndjson",
                       "LOG_HEAD.json", "VERIFY_INSTRUCTIONS.md", "abp_v1.json"):
            continue
        try:
            data = json.loads(c.read_text())
            if data.get("schema_version") == "1.0" and "authority_envelope" in data:
                return c
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def verify_pack(
    pack_dir: Path,
    key_b64: str | None = None,
    public_key_b64: str | None = None,
    strict: bool = False,
    require_abp: bool = False,
) -> VerifyPackResult:
    """Verify all artifacts in a pack directory.

    Auto-discovers:
    - Sealed run JSON (schema_version=1.0 with authority_envelope)
    - Signature file (<sealed>.sig.json)
    - Transparency log (transparency_log.ndjson)
    - Authority ledger (authority_ledger.ndjson)
    """
    result = VerifyPackResult()

    if not pack_dir.exists() or not pack_dir.is_dir():
        result.add_section("discovery", [("pack_dir", False, f"Not found: {pack_dir}")])
        return result

    # Discover sealed run
    sealed_path = _find_sealed(pack_dir)
    if not sealed_path:
        result.add_section("discovery", [("sealed_run", False, "No sealed run found in pack")])
        return result

    discovery_checks: list[tuple[str, bool, str]] = [
        ("sealed_run", True, str(sealed_path.name)),
    ]

    # Discover sig
    sig_path = Path(str(sealed_path) + ".sig.json")
    has_sig = sig_path.exists()
    discovery_checks.append(("signature", has_sig,
                             sig_path.name if has_sig else "Not found (optional)"))

    # Discover log (optional — absence is not a failure)
    log_path = pack_dir / "transparency_log.ndjson"
    has_log = log_path.exists()
    discovery_checks.append(("transparency_log", True,
                             "transparency_log.ndjson" if has_log else "Not present (optional)"))

    # Discover authority ledger (optional — absence is not a failure)
    ledger_path = pack_dir / "authority_ledger.ndjson"
    has_ledger = ledger_path.exists()
    discovery_checks.append(("authority_ledger", True,
                             "authority_ledger.ndjson" if has_ledger else "Not present (optional)"))

    # Discover ABP
    abp_path = pack_dir / "abp_v1.json"
    has_abp = abp_path.exists()
    if require_abp:
        discovery_checks.append(("abp", has_abp,
                                 "abp_v1.json" if has_abp else "MISSING (required by --require-abp)"))
    else:
        discovery_checks.append(("abp", True,
                                 "abp_v1.json" if has_abp else "Not present (recommended: use --require-abp to enforce)"))

    result.add_section("Discovery", discovery_checks)

    # ── 1. Replay sealed run ──────────────────────────────────────
    replay_result = replay(
        sealed_path,
        verify_hash=True,
        verify_sig=has_sig and (key_b64 is not None or public_key_b64 is not None),
        key_b64=key_b64,
        public_key_b64=public_key_b64,
        verify_transparency=has_log,
        transparency_log=log_path if has_log else None,
        verify_authority=has_ledger,
        authority_ledger=ledger_path if has_ledger else None,
    )
    result.add_section("Replay + Integrity", replay_result.checks)

    # ── 1b. Verify all detached signature files in pack ───────────
    if key_b64 is not None or public_key_b64 is not None:
        detached_sig_checks: list[tuple[str, bool, str]] = []
        for sig_file in sorted(pack_dir.glob("*.sig.json")):
            target_file = Path(str(sig_file)[: -len(".sig.json")])
            if not target_file.exists():
                detached_sig_checks.append(
                    (f"signature.target_exists.{sig_file.name}", False, f"Missing target: {target_file.name}")
                )
                continue
            sig_result = verify_signature(
                artifact_path=target_file,
                sig_path=sig_file,
                key_b64=key_b64,
                public_key_b64=public_key_b64,
            )
            detached_sig_checks.append(
                (
                    f"signature.verify.{sig_file.name}",
                    sig_result.passed,
                    "PASS" if sig_result.passed else "Signature mismatch or invalid signature block",
                )
            )
        if detached_sig_checks:
            result.add_section("Detached Signatures", detached_sig_checks)

    # ── 2. Transparency log chain ─────────────────────────────────
    if has_log:
        log_checks = verify_chain(log_path)
        log_tuples: list[tuple[str, bool, str]] = [
            (f"log_chain.line_{ln}", ok, detail)
            for ln, ok, detail in log_checks
        ]
        result.add_section("Transparency Log Chain", log_tuples)

    # ── 3. Authority ledger chain ─────────────────────────────────
    if has_ledger:
        ledger_result = verify_ledger(ledger_path)
        result.add_section("Authority Ledger", ledger_result.checks)

    # ── 4. Authority Boundary Primitive ──────────────────────────
    if has_abp:
        abp_result = verify_abp(abp_path, ledger_path if has_ledger else None)
        result.add_section("Authority Boundary Primitive", abp_result.checks)

    # ── 5. Determinism audit ──────────────────────────────────────
    audit_result = audit_sealed_run(sealed_path, strict=strict)
    audit_checks: list[tuple[str, bool, str]] = [
        ("determinism.violations", audit_result.violations == 0,
         f"{audit_result.violations} violations"),
    ]
    for name, passed, detail in audit_result.checks:
        audit_checks.append((f"determinism.{name}", passed, detail))
    result.add_section("Determinism Audit", audit_checks)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Pack — one-command admissibility verification"
    )
    parser.add_argument("--pack", type=Path, required=True,
                        help="Pack directory to verify")
    parser.add_argument("--key", default=None,
                        help="Base64 HMAC shared key")
    parser.add_argument("--public-key", default=None,
                        help="Base64 Ed25519 public key")
    parser.add_argument("--strict", action="store_true",
                        help="Strict mode (determinism audit)")
    parser.add_argument("--require-abp", action="store_true",
                        help="Require ABP (abp_v1.json) in the pack — fail if missing")
    args = parser.parse_args()

    result = verify_pack(
        pack_dir=args.pack,
        key_b64=args.key,
        public_key_b64=args.public_key,
        strict=args.strict,
        require_abp=args.require_abp,
    )

    print("=" * 60)
    print("  Admissibility Pack Verification Report")
    print("=" * 60)

    for section_name, checks in result.sections:
        print(f"\n  ── {section_name} ──")
        for name, passed, detail in checks:
            icon = "PASS" if passed else "FAIL"
            print(f"  [{icon}] {name}: {detail}")

    print()
    print("-" * 60)
    total = result.total_checks
    passed = total - result.failed_count
    if result.passed:
        print(f"  RESULT: PACK VERIFIED  ({passed}/{total} checks passed)")
    else:
        print(f"  RESULT: VERIFICATION FAILED  ({result.failed_count} failures)")
    print("=" * 60)

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
