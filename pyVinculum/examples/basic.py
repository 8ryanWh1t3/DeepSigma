from vinculum import Constraint, Hypothesis, VinculumEngine

hypotheses = [
    Hypothesis(
        id="H1",
        statement="Candidate A is operationally admissible.",
        probability=0.72,
        payload={
            "distance": {"value": 90, "unit": "ft"},
            "approved": True,
            "source_count": 4,
        },
        source="language-model",
    ),
    Hypothesis(
        id="H2",
        statement="Candidate B is operationally admissible.",
        probability=0.88,
        payload={
            "distance": {"value": 70, "unit": "ft"},
            "approved": True,
            "source_count": 6,
        },
        source="language-model",
    ),
]

constraints = [
    Constraint(
        id="D1",
        field="distance",
        op="gte",
        expected={"value": 82, "unit": "ft"},
        hard=True,
        description="Minimum standoff distance",
    ),
    Constraint(
        id="D2",
        field="approved",
        op="eq",
        expected=True,
        hard=True,
        description="Explicit approval",
    ),
    Constraint(
        id="D3",
        field="source_count",
        op="gte",
        expected=5,
        hard=False,
        weight=0.5,
        description="Preferred evidence depth",
    ),
]

report = VinculumEngine().bind(hypotheses, constraints)

for row in report.results:
    print(row.hypothesis.id, row.state.value, "bounded_confidence=", row.bounded_confidence, "coherence=", row.coherence_score)

print("best supported:", report.best_supported_id)
print("receipt:", report.sha256())
