from __future__ import annotations

from dataclasses import dataclass


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class DerivedVector:
    p_norm: float
    d_norm: float
    vinculum_signed: float
    vinculum_score: float
    tension_balance: float
    intensity: float
    effective_tension: float
    usable_value: float


def derive_vector(P: float, D: float, coverage: float) -> DerivedVector:
    """Derive the VINCULUM third-state vector.

    Raw P and D are independent pressures in [0, 1]. They are normalized only
    to derive the directional relationship between them.

      p = P / (P + D)
      d = D / (P + D)
      V = d - p                         [-1, +1]
      score = 50 * (V + 1)            [0, 100]
      tau = 1 - abs(V)                 [0, 1] balance tension
      intensity = (P + D) / 2          [0, 1]
      effective_tension = tau * intensity * coverage
      usable = 50 * (1 + V * coverage)

    If P + D == 0, the directional state is neutral and coverage should carry
    the fact that no usable measurement exists.
    """
    P = clamp01(P)
    D = clamp01(D)
    coverage = clamp01(coverage)
    total = P + D
    if total <= 1e-15:
        p = d = 0.5
    else:
        p = P / total
        d = D / total
    V = max(-1.0, min(1.0, d - p))
    score = 50.0 * (V + 1.0)
    tau = 1.0 - abs(V)
    intensity = (P + D) / 2.0
    effective_tension = tau * intensity * coverage
    usable = 50.0 * (1.0 + V * coverage)
    return DerivedVector(
        p_norm=p,
        d_norm=d,
        vinculum_signed=V,
        vinculum_score=score,
        tension_balance=tau,
        intensity=intensity,
        effective_tension=effective_tension,
        usable_value=usable,
    )
