class PyOntologyError(Exception):
    """Base exception for pyOntology."""


class SemanticCollisionError(PyOntologyError):
    """Raised when a concept would duplicate or ambiguously overlap existing meaning."""


class ModuleRegistrationError(PyOntologyError):
    """Raised when a module cannot be registered safely."""
