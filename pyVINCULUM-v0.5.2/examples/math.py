from vinculum import VinculumEngine, ObjectType, ScoreMode, ingest_text

for text in ("2 + 2 = 4", "x ≈ 4 ± 0.5 with 80% confidence"):
    obj = ingest_text(text, object_type=ObjectType.MATH, object_id=text, mode=ScoreMode.MATH)
    r = VinculumEngine().score(obj)
    print(text, r.to_dict(include_children=False)["Sigma_V"], "score=", round(r.vinculum_score, 2), "tension=", round(r.tension_index, 2))
