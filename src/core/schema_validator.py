"""Runtime JSON Schema validation for ingest boundaries.

Lazy-compiles schemas from core/schemas/*.schema.json and validates payloads
at episode ingestion, policy pack loading, drift acceptance, and MCP input.

Usage:
    from core.schema_validator import validate

    result = validate(episode_dict, "episode")
    if not result.valid:
        for err in result.errors:
            print(f"{err.path}: {err.message}")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

logger = logging.getLogger(__name__)

SPECS_DIR = Path(__file__).resolve().parent / "schemas"
_REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_SCHEMA = _REPO_ROOT / "enterprise" / "docs" / "policy_packs" / "policy_pack.schema.json"

# Compiled validator cache: schema_name -> Draft202012Validator
_VALIDATORS: Dict[str, Draft202012Validator] = {}

# External $ref URL prefix → local schemas/core/ directory mapping
_REF_PREFIX = "https://sigma-overwatch.dev/schemas/"


@dataclass
class SchemaError:
    """A single validation error."""

    path: str  # JSON pointer to the failing field
    message: str  # Human-readable error message
    schema_path: str  # JSON pointer into the schema


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool
    errors: List[SchemaError] = field(default_factory=list)
    schema_name: str = ""


def _get_validator(schema_name: str) -> Optional[Draft202012Validator]:
    """Load and cache a schema validator by name."""
    if schema_name in _VALIDATORS:
        return _VALIDATORS[schema_name]

    # Check schemas/core/ first, then policy_packs/ for policy_pack schema
    if schema_name == "policy_pack":
        schema_file = POLICY_SCHEMA
    else:
        schema_file = SPECS_DIR / f"{schema_name}.schema.json"

    if not schema_file.exists():
        logger.warning("Schema not found: %s", schema_file)
        return None

    schema = json.loads(schema_file.read_text(encoding="utf-8"))

    # Build a referencing registry so $ref URLs resolve to local schema files
    registry = _build_registry()
    validator = Draft202012Validator(schema, registry=registry)
    _VALIDATORS[schema_name] = validator
    return validator


# Registry cache (built once)
_REGISTRY: Optional[Registry] = None


def _build_registry() -> Registry:
    """Build a referencing Registry mapping external $ref URLs to local schema files."""
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY

    resources: list = []
    for schema_file in SPECS_DIR.glob("*.schema.json"):
        content = json.loads(schema_file.read_text(encoding="utf-8"))
        uri = f"{_REF_PREFIX}{schema_file.name}"
        resources.append((uri, Resource.from_contents(content)))

    _REGISTRY = Registry().with_resources(resources)
    return _REGISTRY


def validate(payload: Dict[str, Any], schema_name: str) -> ValidationResult:
    """Validate a payload against a named schema.

    Args:
        payload: The JSON-serializable dict to validate.
        schema_name: Name of the schema (e.g., "episode", "drift", "policy_pack").

    Returns:
        ValidationResult with valid=True if no errors.
    """
    validator = _get_validator(schema_name)
    if validator is None:
        return ValidationResult(valid=True, schema_name=schema_name)

    errors = []
    for error in validator.iter_errors(payload):
        errors.append(SchemaError(
            path="/".join(str(p) for p in error.absolute_path) or "/",
            message=error.message,
            schema_path="/".join(str(p) for p in error.absolute_schema_path),
        ))

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        schema_name=schema_name,
    )


def is_validation_enabled() -> bool:
    """Check if runtime schema validation is enabled via environment."""
    return os.environ.get("DEEPSIGMA_VALIDATE_SCHEMAS", "").lower() in (
        "1",
        "true",
        "yes",
    )


def clear_cache() -> None:
    """Clear the compiled validator cache (useful for testing)."""
    global _REGISTRY
    _VALIDATORS.clear()
    _REGISTRY = None
