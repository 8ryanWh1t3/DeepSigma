from vinculum import VinculumEngine, ObjectType, ScoreMode, ingest_text

text = "The sensor likely detected a vehicle approximately 80 meters north of checkpoint A."
obj = ingest_text(text, object_type=ObjectType.CLAIM, object_id="CLAIM-001", mode=ScoreMode.LANGUAGE)
result = VinculumEngine().score(obj)
print(result.to_dict(include_children=False))
