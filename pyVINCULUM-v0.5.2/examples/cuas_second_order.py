"""High-stakes second-order example: words say clear, sensor count says one.

Run from the project root with:
    PYTHONPATH=src python examples/cuas_second_order.py
"""
from vinculum import MeaningRegistry, MeaningRule, ObjectType, VinculumEngine, ingest_mapping

clear_rule = MeaningRule.compile(
    id="SEM_AIRSPACE_CLEAR",
    label="airspace clear",
    pattern=r"\bairspace\s+(?:is\s+)?clear\b",
    dimension="count",
    operator="eq",
    value=0,
    unit="count",
    confidence=0.95,  # S_L: strength of word -> numeric expectation
    priority=5,
)

engine = VinculumEngine(meaning_registry=MeaningRegistry.default().with_rule(clear_rule))

for sensor_confidence in (0.99, 0.42):
    obj = ingest_mapping(
        {
            "claims": ["Airspace clear."],
            "observations": [
                {
                    "label": "active threat tracks",
                    "count": 1,
                    "sensor_confidence": sensor_confidence,  # R_D
                }
            ],
        },
        object_type=ObjectType.EPISODE,
        object_id=f"CUAS-{sensor_confidence}",
    )
    result = engine.score(obj)
    primary = result.primary_collision or {}
    print({
        "sensor_confidence": sensor_confidence,
        "status": result.collision_status,
        "expected": primary.get("semantic_value"),
        "observed": primary.get("record_value"),
        "S_L": result.semantic_determinization_strength,
        "R_D": result.deterministic_defense_strength,
        "U_D": result.probabilistic_contamination,
        "D_raw": result.raw_deterministic_strength,
        "D_effective": result.defended_deterministic_strength,
        "collision_strength": result.collision_strength,
        "pair_alignment": primary.get("alignment_score"),
    })
