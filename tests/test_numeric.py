from mayhaps import compose, numeric


def test_positive_passes():
    assert compose(5, numeric.positive) == 5


def test_positive_rejects_zero():
    assert compose(0, numeric.positive) is None


def test_positive_rejects_negative():
    assert compose(-1, numeric.positive) is None


def test_non_negative_passes_zero():
    assert compose(0, numeric.non_negative) == 0


def test_non_negative_passes_positive():
    assert compose(3, numeric.non_negative) == 3


def test_non_negative_rejects_negative():
    assert compose(-1, numeric.non_negative) is None


def test_clamp_within_range():
    assert compose(50, numeric.clamp(0, 100)) == 50


def test_clamp_at_bounds():
    assert compose(0, numeric.clamp(0, 100)) == 0
    assert compose(100, numeric.clamp(0, 100)) == 100


def test_clamp_above_max():
    assert compose(150, numeric.clamp(0, 100)) is None


def test_clamp_below_min():
    assert compose(-1, numeric.clamp(0, 100)) is None
