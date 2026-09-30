from __future__ import annotations

from difflib import SequenceMatcher

from .model import TermRecord
from .util import normalize_text


def text_similarity(a: str | None, b: str | None) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def term_similarity(a: TermRecord, b: TermRecord) -> tuple[float, str]:
    label_scores = [text_similarity(x, y) for x in a.all_labels() for y in b.all_labels()]
    label = max(label_scores) if label_scores else 0.0
    definition = text_similarity(a.definition or a.comment, b.definition or b.comment)
    kind_overlap = 1.0 if set(a.kinds) & set(b.kinds) else 0.0
    # Label dominates because this is discovery, not autonomous equivalence adjudication.
    score = (0.65 * label) + (0.25 * definition) + (0.10 * kind_overlap)
    reason = f"label={label:.2f}; definition={definition:.2f}; kind_overlap={kind_overlap:.0f}"
    return round(score, 4), reason
