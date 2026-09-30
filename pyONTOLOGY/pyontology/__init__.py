"""Deep Sigma pyOntology — modular ontology federation without semantic silos."""

from .fabric import SemanticFabric
from .module import OntologyModule
from .registry import SemanticRegistry
from .diff import diff_modules
from .validation import validate_module, validate_fabric, validate_shacl
from .exceptions import PyOntologyError, SemanticCollisionError, ModuleRegistrationError

Fabric = SemanticFabric

__all__ = [
    "Fabric", "SemanticFabric", "OntologyModule", "SemanticRegistry",
    "diff_modules", "validate_module", "validate_fabric", "validate_shacl",
    "PyOntologyError", "SemanticCollisionError", "ModuleRegistrationError",
]

__version__ = "0.1.0"
