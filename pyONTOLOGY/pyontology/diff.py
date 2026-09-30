from __future__ import annotations

from .model import DiffReport


def diff_modules(old, new) -> DiffReport:
    old_triples = set(old.graph)
    new_triples = set(new.graph)
    old_terms = {t.uri: t for t in old.terms()}
    new_terms = {t.uri: t for t in new.terms()}

    old_uris, new_uris = set(old_terms), set(new_terms)
    changed = sorted(
        uri for uri in old_uris & new_uris
        if old_terms[uri].fingerprint != new_terms[uri].fingerprint
    )
    return DiffReport(
        old_fingerprint=old.fingerprint,
        new_fingerprint=new.fingerprint,
        added_triples=len(new_triples - old_triples),
        removed_triples=len(old_triples - new_triples),
        added_terms=sorted(new_uris - old_uris),
        removed_terms=sorted(old_uris - new_uris),
        changed_terms=changed,
    )
