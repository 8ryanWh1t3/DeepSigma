class VinculumError(Exception):
    """Base error for VINCULUM."""


class InvalidProbability(VinculumError, ValueError):
    """Raised when a probability is outside [0, 1]."""


class InvalidConstraint(VinculumError, ValueError):
    """Raised when a constraint is malformed."""


class UnitError(VinculumError, ValueError):
    """Raised when a quantity unit is unsupported or dimensionally incompatible."""


class GovernanceError(VinculumError, ValueError):
    """Base error for malformed governance inputs."""


class EvidenceIntegrityError(GovernanceError):
    """Raised when evidence content does not match its declared digest."""


class DuplicateRecordError(GovernanceError):
    """Raised when a governance context contains duplicate stable identifiers."""


class TrustError(GovernanceError):
    """Raised when trusted-governance verification or durability fails."""
