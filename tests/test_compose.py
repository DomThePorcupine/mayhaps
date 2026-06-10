from mayhaps import compose


def double(x: int) -> int:
    return x * 2


def returns_none(_: int) -> None:
    return None


def test_no_dependencies_returns_value():
    assert compose(5) == 5


def test_none_input_short_circuits():
    assert compose(None, double) is None


def test_single_dependency_applied():
    assert compose(3, double) == 6


def test_multiple_dependencies_applied_in_order():
    assert compose(3, double, double) == 12


def test_none_from_dependency_short_circuits():
    calls: list[str] = []

    def record_and_return_none(x: int) -> None:
        calls.append("first")
        return None

    def should_not_be_called(x: int) -> int:
        calls.append("second")
        return x

    result = compose(1, record_and_return_none, should_not_be_called)
    assert result is None
    assert calls == ["first"]


def test_returns_none_when_intermediate_dependency_returns_none():
    assert compose(5, double, returns_none, double) is None
