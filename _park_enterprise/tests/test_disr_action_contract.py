from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from deepsigma.security.action_contract import create_action_contract, validate_action_contract


def _now() -> datetime:
    return datetime(2026, 2, 23, 0, 0, tzinfo=timezone.utc)


def test_create_and_validate_contract_round_trip() -> None:
    contract = create_action_contract(
        action_type="ROTATE_KEYS",
        requested_by="ops.user",
        dri="dri.approver",
        approver="dri.approver",
        signing_key="test-signing-key",
        ttl=600,
        now=_now(),
    ).to_dict()

    validated = validate_action_contract(
        contract,
        expected_action_type="ROTATE_KEYS",
        signing_key="test-signing-key",
        now=_now() + timedelta(seconds=120),
    )
    assert validated.action_type == "ROTATE_KEYS"
    assert validated.dri == "dri.approver"


def test_validate_contract_rejects_expired() -> None:
    contract = create_action_contract(
        action_type="REENCRYPT",
        requested_by="ops.user",
        dri="dri.approver",
        approver="dri.approver",
        signing_key="test-signing-key",
        ttl=10,
        now=_now(),
    ).to_dict()

    with pytest.raises(ValueError, match="expired"):
        validate_action_contract(
            contract,
            expected_action_type="REENCRYPT",
            signing_key="test-signing-key",
            now=_now() + timedelta(seconds=20),
        )


def test_validate_contract_rejects_signature_mismatch() -> None:
    contract = create_action_contract(
        action_type="REENCRYPT",
        requested_by="ops.user",
        dri="dri.approver",
        approver="dri.approver",
        signing_key="test-signing-key",
        ttl=600,
        now=_now(),
    ).to_dict()
    contract["signature"] = "bad"

    with pytest.raises(ValueError, match="signature"):
        validate_action_contract(
            contract,
            expected_action_type="REENCRYPT",
            signing_key="test-signing-key",
            now=_now() + timedelta(seconds=1),
        )
