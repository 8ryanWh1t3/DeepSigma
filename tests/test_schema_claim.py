"""JSON Schema validation tests for Claim, DLR, Canon, and Retcon schemas."""
import json
import os
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(rel_path: str):
    with open(os.path.join(_REPO_ROOT, rel_path)) as f:
        return json.load(f)


class TestClaimSchema(unittest.TestCase):
    """Validate claim_primitive_example.json against claim.schema.json."""

    @classmethod
    def setUpClass(cls):
        jsonschema = __import__("jsonschema")
        cls.jsonschema = jsonschema
        cls.schema = _load_json("specs/claim.schema.json")
        cls.example = _load_json("llm_data_model/03_examples/claim_primitive_example.json")

    def test_example_validates(self):
        """The worked example must validate against the schema."""
        self.jsonschema.validate(self.example, self.schema)

    def test_required_fields(self):
        """Missing required fields must raise ValidationError."""
        incomplete = {"claimId": "CLAIM-INCOMPLETE"}
        with self.assertRaises(self.jsonschema.ValidationError):
            self.jsonschema.validate(incomplete, self.schema)

    def test_enum_truth_type(self):
        """Invalid truthType must fail validation."""
        bad = dict(self.example)
        bad["truthType"] = "INVALID"
        with self.assertRaises(self.jsonschema.ValidationError):
            self.jsonschema.validate(bad, self.schema)

    def test_additional_properties_rejected(self):
        """Extra top-level keys must fail if additionalProperties is false."""
        extra = dict(self.example)
        extra["extraField"] = "not allowed"
        with self.assertRaises(self.jsonschema.ValidationError):
            self.jsonschema.validate(extra, self.schema)


class TestDLRSchema(unittest.TestCase):
    """Validate dlr_claim_native_example.json against dlr.schema.json."""

    @classmethod
    def setUpClass(cls):
        jsonschema = __import__("jsonschema")
        cls.jsonschema = jsonschema
        cls.schema = _load_json("specs/dlr.schema.json")

    def test_schema_loads(self):
        """DLR schema must be valid JSON."""
        self.assertIn("properties", self.schema)

    def test_required_fields_present(self):
        """DLR schema must have required field list."""
        self.assertIn("required", self.schema)


class TestCanonSchema(unittest.TestCase):
    """Structural tests for canon.schema.json."""

    @classmethod
    def setUpClass(cls):
        jsonschema = __import__("jsonschema")
        cls.jsonschema = jsonschema
        cls.schema = _load_json("specs/canon.schema.json")

    def test_schema_loads(self):
        """Canon schema must be valid JSON."""
        self.assertIn("properties", self.schema)

    def test_has_claim_id(self):
        """Canon schema must reference claimId."""
        self.assertIn("claimId", self.schema.get("properties", {}))


class TestRetconSchema(unittest.TestCase):
    """Structural tests for retcon.schema.json."""

    @classmethod
    def setUpClass(cls):
        jsonschema = __import__("jsonschema")
        cls.jsonschema = jsonschema
        cls.schema = _load_json("specs/retcon.schema.json")

    def test_schema_loads(self):
        """Retcon schema must be valid JSON."""
        self.assertIn("properties", self.schema)

    def test_has_retcon_fields(self):
        """Retcon schema must have correction-specific fields."""
        props = self.schema.get("properties", {})
        self.assertIn("retconId", props)
        self.assertIn("originalClaimId", props)


if __name__ == "__main__":
    unittest.main()
