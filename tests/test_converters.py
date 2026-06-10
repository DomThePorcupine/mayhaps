from mayhaps import compose, converters


def test_to_int_valid():
    assert compose("42", converters.to_int) == 42


def test_to_int_invalid():
    assert compose("oops", converters.to_int) is None


def test_to_int_none_input():
    assert compose(None, converters.to_int) is None


def test_to_float_valid():
    assert compose("3.14", converters.to_float) == 3.14


def test_to_float_invalid():
    assert compose("abc", converters.to_float) is None


def test_to_str():
    assert compose(42, converters.to_str) == "42"


def test_to_percent():
    assert compose(85, converters.to_percent) == "85%"  # type: ignore[arg-type]


def test_to_percent_float():
    assert compose(99.5, converters.to_percent) == "99.5%"  # type: ignore[arg-type]
