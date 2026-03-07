"""Tests for core.cerpa.models — CERPA primitive dataclasses."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.cerpa.models import (  # noqa: E402
    ApplyResult,
    CerpaCycle,
    Claim,
    Event,
    Patch,
    Review,
)
from core.cerpa.types import (  # noqa: E402
    CerpaDomain,
    CerpaStatus,
    PatchAction,
    ReviewVerdict,
)


# ── Factories ────────────────────────────────────────────────────


def _make_claim(**overrides: object) -> Claim:
    defaults = dict(
        id="claim-001",
        text="System uptime >= 99.9%",
        domain="reops",
        source="sla-monitor",
        timestamp="2026-03-01T10:00:00Z",
    )
    defaults.update(overrides)
    return Claim(**defaults)  # type: ignore[arg-type]


def _make_event(**overrides: object) -> Event:
    defaults = dict(
        id="event-001",
        text="Uptime dropped to 99.5%",
        domain="reops",
        source="apm",
        timestamp="2026-03-02T10:00:00Z",
    )
    defaults.update(overrides)
    return Event(**defaults)  # type: ignore[arg-type]


def _make_review(**overrides: object) -> Review:
    defaults = dict(
        id="rev-001",
        claim_id="claim-001",
        event_id="event-001",
        domain="reops",
        timestamp="2026-03-02T10:01:00Z",
        verdict="mismatch",
        rationale="Uptime below threshold",
        drift_detected=True,
    )
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def _make_patch(**overrides: object) -> Patch:
    defaults = dict(
        id="patch-001",
        review_id="rev-001",
        domain="reops",
        timestamp="2026-03-02T10:02:00Z",
        action="adjust",
        target="claim-001",
        description="Scale service to restore uptime",
    )
    defaults.update(overrides)
    return Patch(**defaults)  # type: ignore[arg-type]


def _make_apply(**overrides: object) -> ApplyResult:
    defaults = dict(
        id="apply-001",
        patch_id="patch-001",
        domain="reops",
        timestamp="2026-03-02T10:03:00Z",
        success=True,
    )
    defaults.update(overrides)
    return ApplyResult(**defaults)  # type: ignore[arg-type]


# ── Enum tests ───────────────────────────────────────────────────


class TestEnums:
    def test_cerpa_domain_values(self) -> None:
        assert set(CerpaDomain) == {
            CerpaDomain.INTELOPS,
            CerpaDomain.REOPS,
            CerpaDomain.FRANOPS,
            CerpaDomain.AUTHORITYOPS,
            CerpaDomain.ACTIONOPS,
        }
        assert isinstance(CerpaDomain.INTELOPS, str)

    def test_cerpa_status_values(self) -> None:
        assert CerpaStatus.ALIGNED.value == "aligned"
        assert CerpaStatus.APPLIED.value == "applied"
        assert isinstance(CerpaStatus.PATCHED, str)

    def test_review_verdict_values(self) -> None:
        assert ReviewVerdict.MISMATCH.value == "mismatch"
        assert ReviewVerdict.VIOLATION.value == "violation"
        assert isinstance(ReviewVerdict.ALIGNED, str)

    def test_patch_action_values(self) -> None:
        assert PatchAction.ADJUST.value == "adjust"
        assert PatchAction.STRENGTHEN.value == "strengthen"
        assert isinstance(PatchAction.EXPIRE, str)


# ── Claim tests ──────────────────────────────────────────────────


class TestClaim:
    def test_create_defaults(self) -> None:
        c = _make_claim()
        assert c.id == "claim-001"
        assert c.assumptions == []
        assert c.authority is None
        assert c.provenance == []
        assert c.related_ids == []
        assert c.metadata == {}

    def test_to_dict_required_fields(self) -> None:
        c = _make_claim()
        d = c.to_dict()
        assert d["id"] == "claim-001"
        assert d["text"] == "System uptime >= 99.9%"
        assert d["domain"] == "reops"
        assert "assumptions" not in d  # empty list omitted

    def test_to_dict_optional_fields(self) -> None:
        c = _make_claim(assumptions=["no downtime"], authority="ops-lead")
        d = c.to_dict()
        assert d["assumptions"] == ["no downtime"]
        assert d["authority"] == "ops-lead"

    def test_all_domains_accepted(self) -> None:
        for domain in CerpaDomain:
            c = _make_claim(domain=domain.value)
            assert c.domain == domain.value


# ── Event tests ──────────────────────────────────────────────────


class TestEvent:
    def test_create_defaults(self) -> None:
        e = _make_event()
        assert e.id == "event-001"
        assert e.observed_state == {}
        assert e.metadata == {}

    def test_to_dict(self) -> None:
        e = _make_event(observed_state={"uptime": 99.5})
        d = e.to_dict()
        assert d["observed_state"] == {"uptime": 99.5}


# ── Review tests ─────────────────────────────────────────────────


class TestReview:
    def test_create_defaults(self) -> None:
        r = _make_review()
        assert r.severity is None
        assert r.source == ""
        assert r.drift_detected is True

    def test_to_dict(self) -> None:
        r = _make_review(severity="yellow")
        d = r.to_dict()
        assert d["verdict"] == "mismatch"
        assert d["drift_detected"] is True
        assert d["severity"] == "yellow"


# ── Patch tests ──────────────────────────────────────────────────


class TestPatch:
    def test_create_defaults(self) -> None:
        p = _make_patch()
        assert p.source == ""
        assert p.metadata == {}

    def test_to_dict(self) -> None:
        p = _make_patch()
        d = p.to_dict()
        assert d["action"] == "adjust"
        assert d["target"] == "claim-001"


# ── ApplyResult tests ────────────────────────────────────────────


class TestApplyResult:
    def test_create_defaults(self) -> None:
        a = _make_apply()
        assert a.success is True
        assert a.new_state == {}
        assert a.updated_claims == []

    def test_to_dict(self) -> None:
        a = _make_apply(new_state={"restored": True}, updated_claims=["c-1"])
        d = a.to_dict()
        assert d["success"] is True
        assert d["new_state"] == {"restored": True}
        assert d["updated_claims"] == ["c-1"]


# ── CerpaCycle tests ─────────────────────────────────────────────


class TestCerpaCycle:
    def test_aligned_cycle(self) -> None:
        cycle = CerpaCycle(
            cycle_id="cycle-001",
            domain="reops",
            claim=_make_claim(),
            event=_make_event(),
            review=_make_review(verdict="aligned", drift_detected=False),
            status="aligned",
        )
        assert cycle.patch is None
        assert cycle.apply_result is None
        d = cycle.to_dict()
        assert d["status"] == "aligned"
        assert "patch" not in d
        assert "apply_result" not in d

    def test_patched_cycle(self) -> None:
        cycle = CerpaCycle(
            cycle_id="cycle-002",
            domain="reops",
            claim=_make_claim(),
            event=_make_event(),
            review=_make_review(),
            patch=_make_patch(),
            apply_result=_make_apply(),
            status="applied",
        )
        d = cycle.to_dict()
        assert d["status"] == "applied"
        assert "patch" in d
        assert "apply_result" in d
        assert d["patch"]["action"] == "adjust"
        assert d["apply_result"]["success"] is True
