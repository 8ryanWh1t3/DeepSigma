from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from .authority import AuthorityEngine
from .models import MissionObject, MissionObjectKind, Patch, Review, Scope, utcnow
from .reconcile import Conflict


class CerpaState(str, Enum):
    CLAIM = "CLAIM"
    EVENT = "EVENT"
    REVIEW = "REVIEW"
    PATCH = "PATCH"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


@dataclass(slots=True)
class CerpaCase:
    case_id: str
    conflict: Conflict
    state: CerpaState = CerpaState.CLAIM
    reviews: list[Review] = field(default_factory=list)
    patch: Patch | None = None


class CerpaEngine:
    def __init__(self, authority: AuthorityEngine) -> None:
        self.authority = authority
        self._cases: dict[str, CerpaCase] = {}

    def open(self, conflict: Conflict) -> CerpaCase:
        case = CerpaCase(case_id=str(uuid4()), conflict=conflict, state=CerpaState.EVENT)
        self._cases[case.case_id] = case
        return case

    def review(self, case_id: str, *, reviewer: str, rationale: str, selected_object_id: str | None = None) -> Review:
        case = self._cases[case_id]
        review = Review(
            review_id=str(uuid4()),
            conflict_id=case.conflict.conflict_id,
            reviewer=reviewer,
            rationale=rationale,
            selected_object_id=selected_object_id,
        )
        case.reviews.append(review)
        case.state = CerpaState.REVIEW
        return review

    def propose_patch(
        self,
        case_id: str,
        *,
        author: str,
        value,
        authority_id: str,
        rationale: str,
    ) -> Patch:
        case = self._cases[case_id]
        decision = self.authority.decide(
            subject=author,
            authority_id=authority_id,
            required_scope=Scope.PATCH,
            context={"entity_id": case.conflict.entity_id, "field": case.conflict.field},
        )
        if not decision.allowed:
            raise PermissionError(decision.reason)
        patch = Patch.create(
            conflict_id=case.conflict.conflict_id,
            author=author,
            entity_id=case.conflict.entity_id,
            field=case.conflict.field,
            value=value,
            authority_id=authority_id,
            rationale=rationale,
            supersedes=tuple(o.object_id for o in case.conflict.candidates),
        )
        case.patch = patch
        case.state = CerpaState.PATCH
        return patch

    def apply(self, case_id: str, *, actor: str) -> MissionObject:
        case = self._cases[case_id]
        if case.patch is None:
            raise ValueError("no patch proposed")
        patch = case.patch
        decision = self.authority.decide(
            subject=actor,
            authority_id=patch.authority_id,
            required_scope=Scope.APPLY,
            context={"entity_id": patch.entity_id, "field": patch.field},
        )
        if not decision.allowed:
            raise PermissionError(decision.reason)

        now = utcnow()
        obj = MissionObject(
            object_id=patch.patch_id,
            kind=MissionObjectKind.PATCH,
            entity_id=patch.entity_id,
            field=patch.field,
            value=patch.value,
            origin_peer=actor,
            observed_at=now,
            created_at=now,
            confidence=1.0,
            authority_id=patch.authority_id,
            dependencies=patch.supersedes,
            version=max((o.version for o in case.conflict.candidates), default=0) + 1,
            metadata={"rationale": patch.rationale, "cerpa_case_id": case.case_id},
        )
        case.state = CerpaState.APPLIED
        return obj

    def get(self, case_id: str) -> CerpaCase:
        return self._cases[case_id]
