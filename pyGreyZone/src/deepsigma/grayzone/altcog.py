"""Standard competing explanations and checks, never automatic verdicts."""

from __future__ import annotations

from .schema import Alternative


def challenge() -> tuple[Alternative, ...]:
    return (
        Alternative("Routine operations, maintenance, training or environmental conditions",
                    "Compare approved activity schedule and ordinary-rate baseline for the same period."),
        Alternative("Common upstream feed or duplicate reporting makes events appear independent",
                    "Trace record identifiers and lineage groups to the original collection path."),
        Alternative("Unrelated events share a label, entity alias or broad location",
                    "Verify entity resolution and seek discriminating observations across sources."),
    )
