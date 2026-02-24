#!/usr/bin/env python3
"""Detect common crypto misuse patterns and emit security gate reports."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepsigma.security.events import EVENT_NONCE_REUSE_DETECTED, append_security_event  # noqa: E402
from deepsigma.security.policy import load_crypto_policy  # noqa: E402
ENVELOPE_REQUIRED_FIELDS = ["key_id", "key_version", "alg", "nonce", "aad"]


class Finding:
    def __init__(self, *, severity: str, category: str, message: str, location: str) -> None:
        self.severity = severity
        self.category = category
        self.message = message
        self.location = location

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "location": self.location,
        }


def _iter_json_objects(path: Path) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    try:
        if path.suffix == ".jsonl":
            for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append((f"{path}:{idx}", obj))
                except json.JSONDecodeError:
                    continue
        elif path.suffix == ".json":
            obj = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                out.append((str(path), obj))
            elif isinstance(obj, list):
                for idx, item in enumerate(obj, start=1):
                    if isinstance(item, dict):
                        out.append((f"{path}#{idx}", item))
    except Exception:
        return []
    return out


def _find_envelopes(node: Any, where: str) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(node, dict):
        if "encrypted_payload" in node and "nonce" in node:
            found.append((where, node))
        for key, value in node.items():
            found.extend(_find_envelopes(value, f"{where}.{key}"))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            found.extend(_find_envelopes(value, f"{where}[{idx}]"))
    return found


def scan_repo(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    policy = _validate_crypto_policy(root, findings)

    schema_path = root / "schemas" / "core" / "crypto_envelope.schema.json"
    if not schema_path.exists():
        findings.append(
            Finding(
                severity="HIGH",
                category="missing_schema",
                message="Missing crypto envelope schema at schemas/core/crypto_envelope.schema.json",
                location=str(schema_path),
            )
        )
    else:
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            required = set(schema.get("required", []))
            missing = [field for field in ENVELOPE_REQUIRED_FIELDS if field not in required]
            if missing:
                findings.append(
                    Finding(
                        severity="HIGH",
                        category="schema_missing_required",
                        message=f"crypto envelope schema missing required fields: {', '.join(missing)}",
                        location=str(schema_path),
                    )
                )
        except Exception as exc:
            findings.append(
                Finding(
                    severity="HIGH",
                    category="schema_parse_error",
                    message=f"Failed to parse crypto envelope schema: {type(exc).__name__}",
                    location=str(schema_path),
                )
            )

    nonce_locations: dict[str, list[str]] = {}
    for path in root.rglob("*.json*"):
        rel = path.relative_to(root)
        if any(part in {".git", "node_modules", "dist", "build", ".venv", "venv", "schemas"} for part in rel.parts):
            continue
        for where, obj in _iter_json_objects(path):
            for env_where, env in _find_envelopes(obj, where):
                missing = [field for field in ENVELOPE_REQUIRED_FIELDS if field not in env]
                if missing:
                    findings.append(
                        Finding(
                            severity="HIGH",
                            category="missing_envelope_fields",
                            message=f"Encrypted envelope missing fields: {', '.join(missing)}",
                            location=env_where,
                        )
                    )
                if policy:
                    _validate_envelope_against_policy(env, env_where, policy, findings)
                nonce = str(env.get("nonce", ""))
                if nonce:
                    nonce_locations.setdefault(nonce, []).append(env_where)

    for nonce, locations in nonce_locations.items():
        if len(locations) > 1:
            findings.append(
                Finding(
                    severity="HIGH",
                    category="nonce_reuse",
                    message=f"Nonce reused across {len(locations)} envelopes: {nonce[:16]}...",
                    location="; ".join(locations[:5]),
                )
            )

    weak_random_pattern = re.compile(r"\brandom\.(random|randint|randrange|getrandbits|choice)\(")
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if any(part in {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__"} for part in rel.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(text.splitlines(), start=1):
            if weak_random_pattern.search(line):
                if any(token in str(rel).lower() for token in ["security", "crypto", "reencrypt", "rotate"]):
                    findings.append(
                        Finding(
                            severity="MEDIUM",
                            category="weak_randomness",
                            message="Potential weak randomness primitive in security-sensitive module",
                            location=f"{rel}:{idx}",
                        )
                    )

    return findings


def _validate_crypto_policy(root: Path, findings: list[Finding]) -> dict[str, Any] | None:
    policy_path = root / "governance" / "security_crypto_policy.json"
    if not policy_path.exists():
        findings.append(
            Finding(
                severity="HIGH",
                category="missing_crypto_policy",
                message="Missing runtime crypto policy at governance/security_crypto_policy.json",
                location=str(policy_path),
            )
        )
        return None

    schema_path = root / "schemas" / "core" / "security_crypto_policy.schema.json"
    if not schema_path.exists():
        findings.append(
            Finding(
                severity="HIGH",
                category="missing_crypto_policy_schema",
                message="Missing crypto policy schema at schemas/core/security_crypto_policy.schema.json",
                location=str(schema_path),
            )
        )

    try:
        policy = load_crypto_policy(policy_path)
    except Exception as exc:
        findings.append(
            Finding(
                severity="HIGH",
                category="invalid_crypto_policy",
                message=f"Invalid crypto policy: {exc}",
                location=str(policy_path),
            )
        )
        return None

    min_ttl = int(policy["min_ttl_days"])
    max_ttl = int(policy["max_ttl_days"])
    if min_ttl > max_ttl:
        findings.append(
            Finding(
                severity="HIGH",
                category="invalid_ttl_bounds",
                message=f"Crypto policy min_ttl_days ({min_ttl}) exceeds max_ttl_days ({max_ttl})",
                location=str(policy_path),
            )
        )

    default_provider = str(policy.get("default_provider", ""))
    allowed_providers = {str(item) for item in policy.get("allowed_providers", [])}
    if default_provider and default_provider not in allowed_providers:
        findings.append(
            Finding(
                severity="HIGH",
                category="invalid_default_provider",
                message=f"default_provider '{default_provider}' is not in allowed_providers",
                location=str(policy_path),
            )
        )

    env_provider = os.getenv("DEEPSIGMA_CRYPTO_PROVIDER")
    if env_provider:
        normalized = env_provider.strip().lower()
        if normalized not in allowed_providers:
            findings.append(
                Finding(
                    severity="HIGH",
                    category="provider_policy_violation_env",
                    message=f"DEEPSIGMA_CRYPTO_PROVIDER '{normalized}' is blocked by crypto policy",
                    location="env:DEEPSIGMA_CRYPTO_PROVIDER",
                )
            )
        elif default_provider and normalized != default_provider:
            findings.append(
                Finding(
                    severity="MEDIUM",
                    category="provider_drift",
                    message=(
                        f"Runtime provider override '{normalized}' differs from policy default "
                        f"'{default_provider}'"
                    ),
                    location="env:DEEPSIGMA_CRYPTO_PROVIDER",
                )
            )

    return policy


def _validate_envelope_against_policy(
    envelope: dict[str, Any],
    location: str,
    policy: dict[str, Any],
    findings: list[Finding],
) -> None:
    supported_versions = {str(item) for item in policy["envelope_versions_supported"]}
    version = str(envelope.get("envelope_version", ""))
    if version and version not in supported_versions:
        findings.append(
            Finding(
                severity="HIGH",
                category="unsupported_envelope_version",
                message=f"Envelope version '{version}' not in crypto policy supported set",
                location=location,
            )
        )

    provider = str(envelope.get("provider", ""))
    allowed_providers = {str(item) for item in policy["allowed_providers"]}
    if provider and provider not in allowed_providers:
        findings.append(
            Finding(
                severity="HIGH",
                category="provider_policy_violation",
                message=f"Envelope provider '{provider}' blocked by crypto policy",
                location=location,
            )
        )

    algorithm = str(envelope.get("alg", ""))
    allowed_algs = {str(item) for item in policy["allowed_algorithms"]}
    if algorithm and algorithm not in allowed_algs:
        findings.append(
            Finding(
                severity="HIGH",
                category="algorithm_policy_violation",
                message=f"Envelope algorithm '{algorithm}' blocked by crypto policy",
                location=location,
            )
        )


def write_reports(findings: list[Finding], out_json: Path, out_md: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps({"findings": [f.as_dict() for f in findings]}, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = ["# Security Gate Report", ""]
    if not findings:
        lines += ["## PASS", "", "- No crypto misuse findings detected.", ""]
    else:
        lines += ["## Findings", ""]
        for finding in findings:
            lines.append(f"- **{finding.severity}** `{finding.category}`: {finding.message}")
            lines.append(f"  - Location: `{finding.location}`")
        lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def emit_nonce_reuse_event(
    *,
    findings: list[Finding],
    tenant_id: str,
    events_path: Path,
    signing_key: str | None,
) -> None:
    nonce_findings = [f for f in findings if f.category == "nonce_reuse"]
    if not nonce_findings:
        return
    append_security_event(
        event_type=EVENT_NONCE_REUSE_DETECTED,
        tenant_id=tenant_id,
        payload={
            "finding_count": len(nonce_findings),
            "locations": [f.location for f in nonce_findings[:10]],
            "scan_scope": "repo",
            "source": "crypto_misuse_scan",
        },
        events_path=events_path,
        signer_id="security-gate",
        signing_key=signing_key,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for crypto misuse patterns")
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repository root")
    parser.add_argument("--out-json", default="release_kpis/SECURITY_GATE_REPORT.json", help="JSON output path")
    parser.add_argument("--out-md", default="release_kpis/SECURITY_GATE_REPORT.md", help="Markdown output path")
    parser.add_argument(
        "--events-path",
        default="data/security/security_events.jsonl",
        help="Path to append NONCE_REUSE_DETECTED events",
    )
    parser.add_argument("--tenant-id", default="tenant-alpha", help="Tenant id attached to emitted security events")
    parser.add_argument(
        "--signing-key-env",
        default="DEEPSIGMA_AUTHORITY_SIGNING_KEY",
        help="Env var containing optional HMAC signing key",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings = scan_repo(root)

    out_json = (root / args.out_json).resolve()
    out_md = (root / args.out_md).resolve()
    write_reports(findings, out_json, out_md)
    emit_nonce_reuse_event(
        findings=findings,
        tenant_id=args.tenant_id,
        events_path=(root / args.events_path).resolve(),
        signing_key=os.environ.get(args.signing_key_env),
    )

    high = [f for f in findings if f.severity == "HIGH"]
    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_md}")
    if high:
        print(f"Security gate failed with {len(high)} HIGH finding(s)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
