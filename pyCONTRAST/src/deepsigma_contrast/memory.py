from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .models import Assumption, Episode, EvidenceRef, Outcome
from .scorer import lexical_episode_similarity, structural_episode_similarity, weighted_similarity


class EpisodeStore(Protocol):
    def add(self, episode: Episode) -> None: ...
    def get(self, episode_id: str) -> Episode | None: ...
    def all(self) -> list[Episode]: ...


class InMemoryEpisodeStore:
    def __init__(self) -> None:
        self._episodes: dict[str, Episode] = {}

    def add(self, episode: Episode) -> None:
        self._episodes[episode.id] = episode

    def get(self, episode_id: str) -> Episode | None:
        return self._episodes.get(episode_id)

    def all(self) -> list[Episode]:
        return list(self._episodes.values())


class JsonlEpisodeStore(InMemoryEpisodeStore):
    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            self._load()

    def add(self, episode: Episode) -> None:
        super().add(episode)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(episode.to_dict(), sort_keys=True) + "\n")

    def _load(self) -> None:
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                super().add(episode_from_dict(json.loads(line)))


def episode_from_dict(data: dict) -> Episode:
    assumptions = [
        Assumption(
            id=a["id"],
            statement=a["statement"],
            confidence=a.get("confidence", 0.5),
            status=a.get("status", "ACTIVE"),
            expires_at=a.get("expires_at"),
            evidence_ids=tuple(a.get("evidence_ids", [])),
        )
        for a in data.get("assumptions", [])
    ]
    evidence = [
        EvidenceRef(
            id=e["id"],
            uri=e.get("uri"),
            weight=e.get("weight", 1.0),
            supports=e.get("supports", True),
            note=e.get("note"),
        )
        for e in data.get("evidence", [])
    ]
    outcome_data = data.get("outcome")
    outcome = (
        Outcome(
            status=outcome_data["status"],
            summary=outcome_data.get("summary", ""),
            metrics=outcome_data.get("metrics", {}),
        )
        if outcome_data
        else None
    )
    return Episode(
        id=data["id"],
        title=data.get("title", data["id"]),
        claim=data.get("claim", ""),
        decision=data.get("decision", ""),
        rationale=data.get("rationale", ""),
        assumptions=assumptions,
        outcome=outcome,
        evidence=evidence,
        tags=set(data.get("tags", [])),
        entities=data.get("entities", []),
        metadata=data.get("metadata", {}),
        occurred_at=data.get("occurred_at"),
        version=data.get("version", "1"),
    )


def find_comparable(
    current: Episode,
    candidates: list[Episode],
    *,
    top_k: int = 5,
) -> list[tuple[Episode, float]]:
    scored = []
    for candidate in candidates:
        if candidate.id == current.id:
            continue
        sim = weighted_similarity(
            lexical_episode_similarity(current, candidate),
            structural_episode_similarity(current, candidate),
        )
        scored.append((candidate, sim))
    scored.sort(key=lambda x: (-x[1], x[0].id))
    return scored[:top_k]
