#!/usr/bin/env python3
"""Deterministic time handling — no "now" inside hash scope.

Two timestamps:
  1) observed_at  — wall clock, NOT included in deterministic hash scope
  2) committed_at — derived/fixed timestamp, included in hash scope

Deterministic builds must pass --clock.
"""
from __future__ import annotations

from datetime import datetime, timezone


# Fixed clock for tests (deterministic default)
FIXED_TEST_CLOCK = "2026-01-01T00:00:00Z"


def parse_clock(clock_str: str | None) -> datetime:
    """Parse a --clock argument into a UTC datetime.

    Args:
        clock_str: ISO8601 string like "2026-02-21T00:00:00Z", or None for wall clock.

    Returns:
        UTC datetime object.
    """
    if clock_str is None:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(clock_str.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def format_utc(dt: datetime) -> str:
    """Format a datetime as UTC ISO8601 with Z suffix."""
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_utc_compact(dt: datetime) -> str:
    """Format a datetime as compact UTC for filenames: YYYYMMDDTHHMMSSZ."""
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


def observed_now() -> str:
    """Wall-clock timestamp (excluded from hash scope)."""
    return format_utc(datetime.now(timezone.utc))
