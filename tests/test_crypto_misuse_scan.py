from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_scanner_module(repo_root: Path):
    mod_path = repo_root / "scripts" / "crypto_misuse_scan.py"
    spec = importlib.util.spec_from_file_location("crypto_misuse_scan", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scanner_detects_missing_envelope_fields(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "schemas" / "core").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    (repo / "data").mkdir(parents=True, exist_ok=True)

    schema = {
        "required": ["envelope_version", "key_id", "key_version", "alg", "nonce", "aad"],
    }
    (repo / "schemas" / "core" / "crypto_envelope.schema.json").write_text(
        json.dumps(schema),
        encoding="utf-8",
    )
    (repo / "schemas" / "core" / "security_crypto_policy.schema.json").write_text("{}", encoding="utf-8")
    (repo / "governance" / "security_crypto_policy.json").write_text(
        json.dumps(
            {
                "policy_version": "1.0",
                "default_provider": "local-keystore",
                "allowed_providers": ["local-keystore"],
                "allowed_algorithms": ["AES-256-GCM"],
                "min_ttl_days": 1,
                "max_ttl_days": 30,
                "envelope_version_current": "1.0",
                "envelope_versions_supported": ["1.0"],
            }
        ),
        encoding="utf-8",
    )

    bad_env = {
        "encrypted_payload": "abc",
        "nonce": "XYZ",
        "alg": "AES-256-GCM",
    }
    (repo / "data" / "records.json").write_text(json.dumps(bad_env), encoding="utf-8")

    module = _load_scanner_module(Path(__file__).resolve().parents[1])
    findings = module.scan_repo(repo)

    categories = {item.category for item in findings}
    assert "missing_envelope_fields" in categories


def test_scanner_passes_with_valid_envelope_and_schema(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "schemas" / "core").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    (repo / "data").mkdir(parents=True, exist_ok=True)

    schema = {
        "required": ["envelope_version", "key_id", "key_version", "alg", "nonce", "aad"],
    }
    (repo / "schemas" / "core" / "crypto_envelope.schema.json").write_text(
        json.dumps(schema),
        encoding="utf-8",
    )
    (repo / "schemas" / "core" / "security_crypto_policy.schema.json").write_text("{}", encoding="utf-8")
    (repo / "governance" / "security_crypto_policy.json").write_text(
        json.dumps(
            {
                "policy_version": "1.0",
                "default_provider": "local-keystore",
                "allowed_providers": ["local-keystore"],
                "allowed_algorithms": ["AES-256-GCM"],
                "min_ttl_days": 1,
                "max_ttl_days": 30,
                "envelope_version_current": "1.0",
                "envelope_versions_supported": ["1.0"],
            }
        ),
        encoding="utf-8",
    )

    good_env = {
        "encrypted_payload": "abc",
        "nonce": "NONCE-1234567890",
        "alg": "AES-256-GCM",
        "key_id": "credibility",
        "key_version": 1,
        "aad": "tenant-alpha",
        "envelope_version": "1.0",
    }
    (repo / "data" / "records.json").write_text(json.dumps(good_env), encoding="utf-8")

    module = _load_scanner_module(Path(__file__).resolve().parents[1])
    findings = module.scan_repo(repo)

    high = [item for item in findings if item.severity == "HIGH"]
    assert not high


def test_scanner_flags_provider_policy_violation(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "schemas" / "core").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    (repo / "data").mkdir(parents=True, exist_ok=True)

    (repo / "schemas" / "core" / "crypto_envelope.schema.json").write_text(
        json.dumps({"required": ["envelope_version", "key_id", "key_version", "alg", "nonce", "aad"]}),
        encoding="utf-8",
    )
    (repo / "schemas" / "core" / "security_crypto_policy.schema.json").write_text("{}", encoding="utf-8")
    (repo / "governance" / "security_crypto_policy.json").write_text(
        json.dumps(
            {
                "policy_version": "1.0",
                "default_provider": "local-keystore",
                "allowed_providers": ["local-keystore"],
                "allowed_algorithms": ["AES-256-GCM"],
                "min_ttl_days": 1,
                "max_ttl_days": 30,
                "envelope_version_current": "1.0",
                "envelope_versions_supported": ["1.0"],
            }
        ),
        encoding="utf-8",
    )
    (repo / "data" / "records.json").write_text(
        json.dumps(
            {
                "encrypted_payload": "abc",
                "nonce": "NONCE-1234567890",
                "alg": "AES-256-GCM",
                "key_id": "credibility",
                "key_version": 1,
                "aad": "tenant-alpha",
                "provider": "aws-kms",
                "envelope_version": "1.0",
            }
        ),
        encoding="utf-8",
    )

    module = _load_scanner_module(Path(__file__).resolve().parents[1])
    findings = module.scan_repo(repo)
    categories = {item.category for item in findings}
    assert "provider_policy_violation" in categories


def test_scanner_flags_provider_drift_from_env(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "schemas" / "core").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    (repo / "data").mkdir(parents=True, exist_ok=True)

    (repo / "schemas" / "core" / "crypto_envelope.schema.json").write_text(
        json.dumps({"required": ["envelope_version", "key_id", "key_version", "alg", "nonce", "aad"]}),
        encoding="utf-8",
    )
    (repo / "schemas" / "core" / "security_crypto_policy.schema.json").write_text("{}", encoding="utf-8")
    (repo / "governance" / "security_crypto_policy.json").write_text(
        json.dumps(
            {
                "policy_version": "1.0",
                "default_provider": "local-keystore",
                "allowed_providers": ["local-keystore", "local-keyring"],
                "allowed_algorithms": ["AES-256-GCM"],
                "min_ttl_days": 1,
                "max_ttl_days": 30,
                "envelope_version_current": "1.0",
                "envelope_versions_supported": ["1.0"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSIGMA_CRYPTO_PROVIDER", "local-keyring")
    module = _load_scanner_module(Path(__file__).resolve().parents[1])
    findings = module.scan_repo(repo)
    categories = {item.category for item in findings}
    assert "provider_drift" in categories


def test_scanner_flags_blocked_provider_override(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "schemas" / "core").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    (repo / "data").mkdir(parents=True, exist_ok=True)

    (repo / "schemas" / "core" / "crypto_envelope.schema.json").write_text(
        json.dumps({"required": ["envelope_version", "key_id", "key_version", "alg", "nonce", "aad"]}),
        encoding="utf-8",
    )
    (repo / "schemas" / "core" / "security_crypto_policy.schema.json").write_text("{}", encoding="utf-8")
    (repo / "governance" / "security_crypto_policy.json").write_text(
        json.dumps(
            {
                "policy_version": "1.0",
                "default_provider": "local-keystore",
                "allowed_providers": ["local-keystore"],
                "allowed_algorithms": ["AES-256-GCM"],
                "min_ttl_days": 1,
                "max_ttl_days": 30,
                "envelope_version_current": "1.0",
                "envelope_versions_supported": ["1.0"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSIGMA_CRYPTO_PROVIDER", "aws-kms")
    module = _load_scanner_module(Path(__file__).resolve().parents[1])
    findings = module.scan_repo(repo)
    categories = {item.category for item in findings}
    assert "provider_policy_violation_env" in categories
