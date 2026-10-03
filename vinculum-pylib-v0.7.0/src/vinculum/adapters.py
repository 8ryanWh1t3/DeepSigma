"""Plugin contract for application-specific language, numeric or graph extraction.

The library never downloads or executes models from a scenario. Implementations are
trusted application code, and their output still passes the strict hinge checks.
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from .core import Representation


@dataclass(frozen=True)
class ExtractionBatch:
    adapter_id: str
    source_id: str
    representations: tuple[Representation, ...]
    unresolved_segments: tuple[str, ...] = ()
    basis: str = 'adapter-supplied typed representations; not independently validated semantics'

    def __post_init__(self):
        object.__setattr__(self, 'representations', tuple(self.representations))
        object.__setattr__(self, 'unresolved_segments', tuple(self.unresolved_segments))
        if not self.adapter_id or not self.source_id or any(not isinstance(r, Representation) for r in self.representations):
            raise ValueError('invalid extraction batch')
        if len({r.id for r in self.representations}) != len(self.representations):
            raise ValueError('adapter returned duplicate representation IDs')


@runtime_checkable
class RepresentationAdapter(Protocol):
    def extract(self, source: str, *, source_id: str) -> ExtractionBatch:
        """Return typed candidates and preserve unhandled material as unresolved."""
        ...


class AdapterRegistry:
    def __init__(self):
        self._adapters = {}

    def register(self, name: str, adapter: RepresentationAdapter):
        if not name or name in self._adapters or not isinstance(adapter, RepresentationAdapter):
            raise ValueError('adapter must implement extract and have a unique name')
        self._adapters[name] = adapter
        return self

    def extract(self, name: str, source: str, *, source_id: str):
        batch = self._adapters[name].extract(source, source_id=source_id)
        if not isinstance(batch, ExtractionBatch):
            raise TypeError('adapter did not return an ExtractionBatch')
        return batch
