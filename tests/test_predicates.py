from mayhaps import compose, when


def test_when_passes():
    assert compose(4, when(lambda n: n % 2 == 0)) == 4


def test_when_rejects():
    assert compose(3, when(lambda n: n % 2 == 0)) is None


def test_when_with_named_predicate():
    def is_weekday(day: str) -> bool:
        return day in {"Mon", "Tue", "Wed", "Thu", "Fri"}

    assert compose("Mon", when(is_weekday)) == "Mon"
    assert compose("Sat", when(is_weekday)) is None


def test_when_none_input():
    assert compose(None, when(lambda n: True)) is None
