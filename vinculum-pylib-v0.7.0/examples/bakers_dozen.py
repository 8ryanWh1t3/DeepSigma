from vinculum import ObjectType, VinculumEngine, ingest_mapping

obj = ingest_mapping(
    {
        "claims": ["The order is a baker's dozen."],
        "receipt": {
            "item": "Baker's Dozen Cookies",
            "quantity": 12,
        },
    },
    object_type=ObjectType.EPISODE,
    object_id="BAKERS-DOZEN-DEMO",
)

r = VinculumEngine().score(obj)
print("status:", r.reconciliation_status)
print("semantic_record_tension:", r.semantic_record_tension)
print("vinculum_score:", round(r.vinculum_score, 2))
print("usable_value:", round(r.usable_value, 2))
print("reconciled_usable_value:", round(r.reconciled_usable_value, 2))
print("comparison:", r.reconciliation["comparisons"][0])
