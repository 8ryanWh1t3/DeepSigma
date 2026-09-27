from deep_sigma_vsa import Confidence


def test_confidence_bounds():
    assert Confidence(0.0).value == 0.0
    assert Confidence(1.0).value == 1.0


def test_confidence_rejects_invalid():
    try:
        Confidence(1.1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
