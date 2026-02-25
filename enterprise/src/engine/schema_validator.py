"""Backward-compat shim — schema_validator moved to core."""
from core.schema_validator import (  # noqa: F401
    SchemaError,
    ValidationResult,
    clear_cache,
    is_validation_enabled,
    validate,
)
