"""In-memory precedent registry."""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import KnowledgeEntry, Precedent


class PrecedentRegistry:
    """In-memory store of precedents and knowledge entries."""

    def __init__(self) -> None:
        self._precedents: Dict[str, Precedent] = {}
        self._knowledge_entries: Dict[str, KnowledgeEntry] = {}

    def add(self, precedent: Precedent) -> str:
        """Add a precedent. Returns the precedent_id."""
        self._precedents[precedent.precedent_id] = precedent
        return precedent.precedent_id

    def get(self, precedent_id: str) -> Optional[Precedent]:
        """Retrieve a precedent by ID, or None if not found."""
        return self._precedents.get(precedent_id)

    def update(self, precedent: Precedent) -> None:
        """Update an existing precedent."""
        self._precedents[precedent.precedent_id] = precedent

    def remove(self, precedent_id: str) -> bool:
        """Remove a precedent. Returns True if it existed."""
        return self._precedents.pop(precedent_id, None) is not None

    def list_all(self) -> List[Precedent]:
        """Return all precedents."""
        return list(self._precedents.values())

    def list_by_category(self, category: str) -> List[Precedent]:
        """Return all precedents in a given category."""
        return [p for p in self._precedents.values() if p.category == category]

    def search_by_similarity(
        self, fingerprint_id: str, threshold: float = 0.5,
    ) -> List[Precedent]:
        """Return precedents whose tags overlap with the given fingerprint.

        This is a placeholder for vector-similarity search.
        For now, returns precedents with relevance_score above threshold.
        """
        return [
            p for p in self._precedents.values()
            if p.relevance_score >= threshold
        ]

    def add_knowledge_entry(self, entry: KnowledgeEntry) -> str:
        """Add a knowledge entry. Returns the entry_id."""
        self._knowledge_entries[entry.entry_id] = entry
        return entry.entry_id

    def get_knowledge_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Retrieve a knowledge entry by ID."""
        return self._knowledge_entries.get(entry_id)

    def list_knowledge_entries(self) -> List[KnowledgeEntry]:
        """Return all knowledge entries."""
        return list(self._knowledge_entries.values())
