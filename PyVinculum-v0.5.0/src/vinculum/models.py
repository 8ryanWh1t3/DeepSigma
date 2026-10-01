from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

from .formulas import DerivedVector


class ObjectType(str, Enum):
    CLAIM = "claim"
    EPISODE = "episode"
    CLAUSE = "clause"
    PARAGRAPH = "paragraph"
    DOCUMENT = "document"
    DATASET = "dataset"
    DATA_ROW = "data_row"
    RDF_TRIPLE = "rdf_triple"
    TTL_GRAPH = "ttl_graph"
    POLICY = "policy"
    DECISION = "decision"
    MODEL_OUTPUT = "model_output"
    SENSOR_OBSERVATION = "sensor_observation"
    CORPUS = "corpus"
    MATH = "math"
    GENERIC = "generic"


class ScoreMode(str, Enum):
    AUTO = "auto"
    LANGUAGE = "language"
    MATH = "math"
    TTL = "ttl"
    STRUCTURED = "structured"


class DominantState(str, Enum):
    UNMEASURED = "UNMEASURED"
    PROBABILISTIC_DOMINANT = "PROBABILISTIC_DOMINANT"
    BOUNDARY_TENSION = "BOUNDARY_TENSION"
    DETERMINISTIC_DOMINANT = "DETERMINISTIC_DOMINANT"


@dataclass(frozen=True)
class Signal:
    id: str
    channel: str
    label: str
    weight: float
    count: int
    examples: tuple[str, ...] = ()
    note: str = ""

    @property
    def contribution(self) -> float:
        return self.weight * self.count


@dataclass(frozen=True)
class VinculumObject:
    object_id: str
    object_type: ObjectType
    content: Any = ""
    mode: ScoreMode = ScoreMode.AUTO
    weight: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    children: tuple["VinculumObject", ...] = ()

    def __post_init__(self) -> None:
        if not self.object_id.strip():
            raise ValueError("object_id cannot be empty")
        if self.weight <= 0:
            raise ValueError("weight must be > 0")
        object.__setattr__(self, "children", tuple(self.children))


@dataclass(frozen=True)
class VinculumResult:
    object_id: str
    object_type: ObjectType
    mode: ScoreMode
    direction: str
    probabilistic_pressure: float
    deterministic_strength: float
    coverage: float
    p_norm: float
    d_norm: float
    vinculum_signed: float
    vinculum_score: float
    tension_balance: float
    intensity: float
    tension_index: float
    usable_value: float
    dominant_state: DominantState
    unresolved_elements: tuple[str, ...] = ()
    drivers_p: tuple[Signal, ...] = ()
    drivers_d: tuple[Signal, ...] = ()
    children: tuple["VinculumResult", ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_vector(
        cls,
        *,
        obj: VinculumObject,
        mode: ScoreMode,
        direction: str,
        P: float,
        D: float,
        coverage: float,
        vector: DerivedVector,
        unresolved: tuple[str, ...] = (),
        drivers_p: tuple[Signal, ...] = (),
        drivers_d: tuple[Signal, ...] = (),
        children: tuple["VinculumResult", ...] = (),
        metadata: Mapping[str, Any] | None = None,
        boundary_low: float = 40.0,
        boundary_high: float = 60.0,
        minimum_coverage: float = 0.15,
    ) -> "VinculumResult":
        if coverage < minimum_coverage:
            state = DominantState.UNMEASURED
        elif vector.vinculum_score < boundary_low:
            state = DominantState.PROBABILISTIC_DOMINANT
        elif vector.vinculum_score > boundary_high:
            state = DominantState.DETERMINISTIC_DOMINANT
        else:
            state = DominantState.BOUNDARY_TENSION
        return cls(
            object_id=obj.object_id,
            object_type=obj.object_type,
            mode=mode,
            direction=direction,
            probabilistic_pressure=P,
            deterministic_strength=D,
            coverage=coverage,
            p_norm=vector.p_norm,
            d_norm=vector.d_norm,
            vinculum_signed=vector.vinculum_signed,
            vinculum_score=vector.vinculum_score,
            tension_balance=vector.tension_balance,
            intensity=vector.intensity,
            tension_index=vector.effective_tension,
            usable_value=vector.usable_value,
            dominant_state=state,
            unresolved_elements=tuple(unresolved),
            drivers_p=tuple(drivers_p),
            drivers_d=tuple(drivers_d),
            children=tuple(children),
            metadata=dict(metadata or {}),
        )

    def to_dict(self, *, include_children: bool = True) -> dict[str, Any]:
        def signal_dict(s: Signal) -> dict[str, Any]:
            return {
                "id": s.id,
                "channel": s.channel,
                "label": s.label,
                "weight": s.weight,
                "count": s.count,
                "contribution": s.contribution,
                "examples": list(s.examples),
                "note": s.note,
            }

        out = {
            "object_id": self.object_id,
            "object_type": self.object_type.value,
            "mode": self.mode.value,
            "direction": self.direction,
            "Sigma_V": {
                "P": self.probabilistic_pressure,
                "D": self.deterministic_strength,
                "V": self.vinculum_signed,
                "tau": self.tension_balance,
                "Coverage": self.coverage,
            },
            "probabilistic_pressure": self.probabilistic_pressure,
            "deterministic_strength": self.deterministic_strength,
            "p_norm": self.p_norm,
            "d_norm": self.d_norm,
            "vinculum_signed": self.vinculum_signed,
            "vinculum_score": self.vinculum_score,
            "tension_balance": self.tension_balance,
            "intensity": self.intensity,
            "tension_index": self.tension_index,
            "usable_value": self.usable_value,
            "coverage": self.coverage,
            "dominant_state": self.dominant_state.value,
            "unresolved_elements": list(self.unresolved_elements),
            "drivers_P": [signal_dict(s) for s in self.drivers_p],
            "drivers_D": [signal_dict(s) for s in self.drivers_d],
            "metadata": dict(self.metadata),
        }
        if include_children:
            out["children"] = [c.to_dict(include_children=True) for c in self.children]
        return out
