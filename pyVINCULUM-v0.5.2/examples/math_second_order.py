from vinculum import ObjectType, ScoreMode, VinculumEngine, ingest_text

engine = VinculumEngine()

for expression in (
    "x = 4",
    "x ≈ 4",
    "x = 4 ± 0.5",
    "x ≈ 4 ± 0.5 with 80% confidence",
    "x = 4 with reliability 55%",
):
    result = engine.score(
        ingest_text(expression, object_type=ObjectType.MATH, mode=ScoreMode.MATH, decompose=False)
    )
    print(expression)
    print(result.to_dict(include_children=False)["second_order"])
