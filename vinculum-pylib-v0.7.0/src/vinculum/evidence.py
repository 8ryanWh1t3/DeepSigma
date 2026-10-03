"""Source identity and dependency closure. Hashes identify bytes; they do not prove truth."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from .utils import identifier, primitive


@dataclass(frozen=True)
class EvidenceSource:
    id: str
    sha256: str | None
    basis: str
    parents: tuple[str, ...] = ()
    locator: str | None = None
    media_type: str = 'application/octet-stream'

    def __post_init__(self):
        identifier(self.id); identifier(self.basis)
        if self.sha256 is not None:
            if len(self.sha256) != 64 or any(c not in '0123456789abcdef' for c in self.sha256):
                raise ValueError('sha256 must be 64 lowercase hexadecimal characters')
        if isinstance(self.parents, str):
            raise TypeError('parents must be a sequence of source IDs')
        p = tuple(self.parents)
        for x in p: identifier(x)
        if self.id in p or len(set(p)) != len(p):
            raise ValueError('self-referential or duplicate evidence parents')
        object.__setattr__(self, 'parents', p)

    @classmethod
    def from_bytes(cls, id, content: bytes, *, basis, **kwargs):
        return cls(id, hashlib.sha256(content).hexdigest(), basis, **kwargs)


class EvidenceRegistry:
    """Immutable-by-ID in-memory source ledger, not a signature/authority service."""
    def __init__(self, sources=()):
        self._sources = {}
        for source in sources: self.register(source)

    @property
    def sources(self):
        return MappingProxyType(self._sources)

    def register(self, source: EvidenceSource):
        if not isinstance(source, EvidenceSource):
            raise TypeError('expected EvidenceSource')
        prior = self._sources.get(source.id)
        if prior is not None and prior != source:
            raise ValueError('changed source requires a new versioned evidence ID')
        self._sources[source.id] = source
        return self

    def closure(self, ids):
        roots, missing, unhashed = set(), set(), set()
        done, active = set(), set()
        # Explicit DFS stack: deep provenance chains do not use Python recursion.
        stack = [(x, False) for x in ids]
        while stack:
            key, exiting = stack.pop()
            if exiting:
                active.remove(key); done.add(key); continue
            if key in active: raise ValueError('cyclic evidence provenance')
            if key in done: continue
            source = self._sources.get(key)
            if source is None:
                missing.add(key); done.add(key); continue
            if source.sha256 is None: unhashed.add(key)
            if not source.parents: roots.add(key)
            active.add(key); stack.append((key, True))
            stack.extend((p, False) for p in source.parents)
        return {'roots': sorted(roots), 'missing': sorted(missing), 'unhashed': sorted(unhashed),
                'complete': bool(ids) and not missing,
                'meaning': 'registered source closure, not source accuracy or authenticity'}

    def validate(self):
        return self.closure(tuple(self._sources))

    def to_dict(self):
        return [primitive(self._sources[k]) for k in sorted(self._sources)]


class EvidenceHingeEvaluator:
    """Factory for a hinge extension aware of registered evidence ancestry.

    The base comparison kernel is unchanged. Registered shared roots are surfaced
    as dependency warnings; a declared product is capped at a bottleneck for such
    pairs. Unknown registered ancestry withholds a supported score, not the raw
    comparison (unless the separate required-source check prevents comparison).
    """
    @staticmethod
    def create(registry, policy, units):
        from dataclasses import replace
        from .hinge import HingeEvaluator
        from .utils import fingerprint

        class RegisteredHinge(HingeEvaluator):
            def evaluate(self, left, right, pair, *, dependency_warnings=(), missing_dependencies=False):
                a, b = registry.closure(left.source_ids), registry.closure(right.source_ids)
                shared = sorted(set(a['roots']) & set(b['roots']))
                notes = list(dependency_warnings)
                if shared:
                    notes.append('registered evidence shared roots: ' + ', '.join(shared))
                missing = missing_dependencies or bool(a['missing'] or b['missing'])
                result = super().evaluate(left, right, pair, dependency_warnings=tuple(notes),
                                          missing_dependencies=missing)
                support = dict(result.support)
                support['registered_evidence'] = {'left': a, 'right': b, 'shared_roots': shared}
                if shared and support['aggregation'] == 'product':
                    values = [support['left']['strength'], support['right']['strength'],
                              pair.alignment_support] + support['declared_higher_order_hinge_strengths']
                    support['joint_strength'] = None if missing or any(x is None for x in values) else min(values)
                    support['aggregation_requested'] = 'product'
                    support['aggregation'] = 'minimum'
                    support['dependency_rule'] = 'shared registered evidence roots require bottleneck, not independent votes'
                joint = support['joint_strength']
                return replace(result, support=support,
                    supported_collision_score=None if joint is None or result.raw_collision_score is None else joint * result.raw_collision_score,
                    input_fingerprint=fingerprint({'base': result.input_fingerprint,
                                                   'registered_evidence': support['registered_evidence']}))
        return RegisteredHinge(policy, units)
