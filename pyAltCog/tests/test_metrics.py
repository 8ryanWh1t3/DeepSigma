from pyaltcog.metrics import (
    altcog_discovery_rate,
    dormant_alternative_recall,
    residual_conversion_rate,
    time_to_alternative_formation,
    weak_signal_promotion_rate,
)


def test_ratios():
    assert altcog_discovery_rate(2, 4) == 0.5
    assert residual_conversion_rate(3, 6) == 0.5
    assert weak_signal_promotion_rate(1, 4) == 0.25
    assert dormant_alternative_recall(2, 5) == 0.4


def test_zero_denominator_safe():
    assert altcog_discovery_rate(1, 0) == 0.0


def test_taf_seconds():
    assert time_to_alternative_formation(
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:10:00+00:00",
    ) == 600.0
