import json
from pathlib import Path
import pytest


def test_published_schema_accepts_canonical_fixture(atlas):
    jsonschema=pytest.importorskip('jsonschema')
    schema=json.loads((Path(__file__).parents[1]/'schemas/atlas.schema.json').read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(atlas.to_dict())

def test_published_schema_rejects_authoritative_flag(atlas):
    jsonschema=pytest.importorskip('jsonschema')
    schema=json.loads((Path(__file__).parents[1]/'schemas/atlas.schema.json').read_text())
    data=atlas.to_dict();data['authoritative']=True
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate(data,schema)
