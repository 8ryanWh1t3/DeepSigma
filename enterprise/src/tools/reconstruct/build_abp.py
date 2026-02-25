#!/usr/bin/env python3
"""Build Authority Boundary Primitive (ABP) v1.

Creates a stack-independent, pre-runtime governance declaration that any
enforcement engine can read to know the boundaries — without needing
DeepSigma's runtime.

Usage:
    python enterprise/src/tools/reconstruct/build_abp.py \\
        --scope '{"contract_id":"CTR-001","program":"SEQUOIA","modules":["hiring","bid","compliance","boe"]}' \\
        --authority-entry-id AUTH-033059a5 \\
        --authority-ledger enterprise/artifacts/authority_ledger/ledger.ndjson \\
        --config abp_config.json \\
        --clock 2026-02-24T00:00:00Z \\
        --out-dir /tmp/abp
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from canonical_json import canonical_dumps, sha256_text  # noqa: E402


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compute_abp_id(scope: dict, authority_ref: dict, created_at: str) -> str:
    seed = canonical_dumps({
        "scope": scope,
        "authority_ref": authority_ref,
        "created_at": created_at,
    })
    return "ABP-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def _compute_abp_hash(abp: dict) -> str:
    copy = dict(abp)
    copy["hash"] = ""
    return sha256_text(canonical_dumps(copy))


def _resolve_authority_ref(
    authority_entry_id: str,
    ledger_path: Path | None,
) -> dict:
    """Look up authority entry hash from the ledger."""
    entry_hash = ""
    ledger_rel = str(ledger_path) if ledger_path else None

    if ledger_path and ledger_path.exists():
        for line in ledger_path.read_text().strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("entry_id") == authority_entry_id:
                entry_hash = entry.get("entry_hash", "")
                break

    if not entry_hash:
        raise ValueError(
            f"Authority entry '{authority_entry_id}' not found in ledger "
            f"'{ledger_path}'"
        )

    return {
        "authority_entry_id": authority_entry_id,
        "authority_entry_hash": entry_hash,
        "authority_ledger_path": ledger_rel,
    }


def _check_contradictions(abp: dict) -> None:
    """Raise ValueError if any tool or objective appears in both allow and deny."""
    allowed_obj_ids = {o["id"] for o in abp["objectives"]["allowed"]}
    denied_obj_ids = {o["id"] for o in abp["objectives"]["denied"]}
    overlap = allowed_obj_ids & denied_obj_ids
    if overlap:
        raise ValueError(f"Objective IDs in both allowed and denied: {overlap}")

    allowed_tools = {t["name"] for t in abp["tools"]["allow"]}
    denied_tools = {t["name"] for t in abp["tools"]["deny"]}
    overlap = allowed_tools & denied_tools
    if overlap:
        raise ValueError(f"Tool names in both allow and deny: {overlap}")


def build_abp(
    scope: dict,
    authority_ref: dict,
    objectives: dict | None = None,
    tools: dict | None = None,
    data: dict | None = None,
    approvals: dict | None = None,
    escalation: dict | None = None,
    runtime: dict | None = None,
    proof: dict | None = None,
    delegation_review: dict | None = None,
    clock: str | None = None,
    effective_at: str | None = None,
    expires_at: str | None = None,
    parent_abp_id: str | None = None,
    parent_abp_hash: str | None = None,
) -> dict:
    """Build a complete ABP v1 object with deterministic ID and hash."""
    created_at = clock or _now_utc()
    eff_at = effective_at or created_at

    abp = {
        "abp_version": "1.0",
        "abp_id": "",
        "scope": scope,
        "authority_ref": authority_ref,
        "objectives": objectives or {"allowed": [], "denied": []},
        "tools": tools or {"allow": [], "deny": []},
        "data": data or {"permissions": []},
        "approvals": approvals or {"required": []},
        "escalation": escalation or {"paths": []},
        "runtime": runtime or {"validators": []},
        "proof": proof or {"required": ["seal", "manifest", "pack_hash", "transparency_log", "authority_ledger"]},
        "composition": {
            "parent_abp_id": parent_abp_id,
            "parent_abp_hash": parent_abp_hash,
            "children": [],
        },
        "effective_at": eff_at,
        "expires_at": expires_at,
        "created_at": created_at,
        "hash": "",
    }

    # Conditionally include delegation_review (optional section)
    if delegation_review is not None:
        abp["delegation_review"] = delegation_review

    abp["abp_id"] = _compute_abp_id(scope, authority_ref, created_at)
    _check_contradictions(abp)
    abp["hash"] = _compute_abp_hash(abp)

    return abp


def write_abp(abp: dict, out_dir: Path) -> Path:
    """Write ABP to abp_v1.json in out_dir. Returns path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "abp_v1.json"
    path.write_text(json.dumps(abp, indent=2) + "\n")
    return path


def compose_abps(
    parent_scope: dict,
    parent_authority_ref: dict,
    children: list[dict],
    clock: str | None = None,
    effective_at: str | None = None,
    expires_at: str | None = None,
) -> dict:
    """Build a parent ABP from child ABPs. Merges boundaries, preserves child refs."""
    merged_objectives: dict = {"allowed": [], "denied": []}
    merged_tools: dict = {"allow": [], "deny": []}
    merged_data: dict = {"permissions": []}
    merged_approvals: dict = {"required": []}
    merged_escalation: dict = {"paths": []}
    merged_runtime: dict = {"validators": []}
    merged_proof: set[str] = set()
    child_refs: list[dict] = []

    merged_deleg_triggers: list[dict] = []
    merged_review_policy: dict | None = None
    seen_drt_ids: set[str] = set()

    for child in children:
        merged_objectives["allowed"].extend(child["objectives"]["allowed"])
        merged_objectives["denied"].extend(child["objectives"]["denied"])
        merged_tools["allow"].extend(child["tools"]["allow"])
        merged_tools["deny"].extend(child["tools"]["deny"])
        merged_data["permissions"].extend(child["data"]["permissions"])
        merged_approvals["required"].extend(child["approvals"]["required"])
        merged_escalation["paths"].extend(child["escalation"]["paths"])
        merged_runtime["validators"].extend(child["runtime"]["validators"])
        merged_proof.update(child["proof"]["required"])
        child_refs.append({
            "abp_id": child["abp_id"],
            "abp_hash": child["hash"],
        })
        # Merge delegation_review triggers (deduplicate by ID)
        dr = child.get("delegation_review")
        if dr:
            for t in dr.get("triggers", []):
                if t["id"] not in seen_drt_ids:
                    merged_deleg_triggers.append(t)
                    seen_drt_ids.add(t["id"])
            rp = dr.get("review_policy")
            if rp and (merged_review_policy is None or
                       (rp.get("timeout_ms") or float("inf")) <
                       (merged_review_policy.get("timeout_ms") or float("inf"))):
                merged_review_policy = rp

    merged_delegation = None
    if merged_deleg_triggers:
        merged_delegation = {
            "triggers": merged_deleg_triggers,
            "review_policy": merged_review_policy or {
                "approver_role": "Reviewer",
                "threshold": 1,
                "timeout_ms": 604800000,
                "output": "abp_patch",
            },
        }

    parent = build_abp(
        scope=parent_scope,
        authority_ref=parent_authority_ref,
        objectives=merged_objectives,
        tools=merged_tools,
        data=merged_data,
        approvals=merged_approvals,
        escalation=merged_escalation,
        runtime=merged_runtime,
        proof={"required": sorted(merged_proof)},
        delegation_review=merged_delegation,
        clock=clock,
        effective_at=effective_at,
        expires_at=expires_at,
    )

    # Inject children and recompute hash
    parent["composition"]["children"] = child_refs
    parent["hash"] = _compute_abp_hash(parent)

    return parent


def verify_abp_hash(abp: dict) -> bool:
    """Recompute and verify ABP content hash."""
    return _compute_abp_hash(abp) == abp.get("hash", "")


def verify_abp_id(abp: dict) -> bool:
    """Recompute and verify ABP ID is deterministic."""
    expected = _compute_abp_id(
        abp["scope"], abp["authority_ref"], abp["created_at"]
    )
    return expected == abp.get("abp_id", "")


def verify_abp_authority(abp: dict, ledger_path: Path) -> bool:
    """Verify ABP's authority_ref exists and is not revoked in the ledger."""
    if not ledger_path.exists():
        return False

    entry_id = abp["authority_ref"]["authority_entry_id"]
    entry_hash = abp["authority_ref"]["authority_entry_hash"]

    for line in ledger_path.read_text().strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if entry.get("entry_id") == entry_id:
            if entry.get("entry_hash") != entry_hash:
                return False
            if entry.get("revoked_at") is not None:
                return False
            return True

    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Authority Boundary Primitive (ABP) v1"
    )
    parser.add_argument("--scope", required=True,
                        help="JSON scope object: {contract_id, program, modules}")
    parser.add_argument("--authority-entry-id", required=True,
                        help="Authority ledger entry ID (e.g. AUTH-033059a5)")
    parser.add_argument("--authority-ledger", type=Path, default=None,
                        help="Path to authority ledger NDJSON")
    parser.add_argument("--config", type=Path, default=None,
                        help="JSON config with objectives/tools/data/approvals/escalation/runtime/proof/delegation_review")
    parser.add_argument("--clock", default=None,
                        help="Fixed clock (ISO8601 UTC)")
    parser.add_argument("--effective-at", default=None,
                        help="Effective date (ISO8601 UTC, defaults to clock)")
    parser.add_argument("--expires-at", default=None,
                        help="Expiry date (ISO8601 UTC, defaults to null)")
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="Output directory for abp_v1.json")
    args = parser.parse_args()

    scope = json.loads(args.scope)

    # Resolve authority ref from ledger
    authority_ref = _resolve_authority_ref(
        args.authority_entry_id,
        args.authority_ledger,
    )

    # Load config sections
    config = {}
    if args.config and args.config.exists():
        config = json.loads(args.config.read_text())

    abp = build_abp(
        scope=scope,
        authority_ref=authority_ref,
        objectives=config.get("objectives"),
        tools=config.get("tools"),
        data=config.get("data"),
        approvals=config.get("approvals"),
        escalation=config.get("escalation"),
        runtime=config.get("runtime"),
        proof=config.get("proof"),
        delegation_review=config.get("delegation_review"),
        clock=args.clock,
        effective_at=args.effective_at,
        expires_at=args.expires_at,
    )

    path = write_abp(abp, args.out_dir)

    print(f"ABP written: {path}")
    print(f"  abp_id:   {abp['abp_id']}")
    print(f"  hash:     {abp['hash']}")
    print(f"  scope:    {abp['scope']['program']} / {abp['scope']['contract_id']}")
    print(f"  auth_ref: {abp['authority_ref']['authority_entry_id']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
