from mayhaps import compose, collections


# first

def test_first_returns_first_element():
    assert compose([1, 2, 3], collections.first) == 1  # type: ignore[arg-type]


def test_first_returns_only_element():
    assert compose(["a"], collections.first) == "a"  # type: ignore[arg-type]


def test_first_returns_none_for_empty():
    assert compose([], collections.first) is None  # type: ignore[arg-type]


def test_first_short_circuits_on_none_input():
    assert compose(None, collections.first) is None  # type: ignore[arg-type]


def test_first_in_pipeline():
    result = compose([10, 20, 30], collections.first, lambda x: x * 2)  # type: ignore[arg-type]
    assert result == 20


def test_first_pipeline_short_circuits_on_empty():
    called: list[int] = []
    result = compose([], collections.first, lambda x: called.append(x) or x)  # type: ignore[arg-type]
    assert result is None
    assert called == []


# find

def test_find_returns_matching_element():
    assert compose([1, 2, 3], collections.find(lambda x: x > 1)) == 2  # type: ignore[arg-type]


def test_find_returns_first_matching_element():
    assert compose([1, 2, 3, 4], collections.find(lambda x: x % 2 == 0)) == 2  # type: ignore[arg-type]


def test_find_returns_none_when_no_match():
    assert compose([1, 2, 3], collections.find(lambda x: x > 10)) is None  # type: ignore[arg-type]


def test_find_returns_none_for_empty_list():
    assert compose([], collections.find(lambda x: True)) is None  # type: ignore[arg-type]


def test_find_short_circuits_on_none_input():
    assert compose(None, collections.find(lambda x: True)) is None


def test_find_works_with_strings():
    words = ["apple", "banana", "cherry"]
    assert compose(words, collections.find(lambda w: w.startswith("b"))) == "banana"  # type: ignore[arg-type]


def test_find_in_pipeline():
    result = compose([1, 2, 3], collections.find(lambda x: x > 1), lambda x: x + 10)  # type: ignore[arg-type]
    assert result == 12


def test_find_pipeline_short_circuits_on_no_match():
    called: list[int] = []
    result = compose([1, 2, 3], collections.find(lambda x: x > 10), lambda x: called.append(x) or x)  # type: ignore[arg-type]
    assert result is None
    assert called == []


# non_empty (list version)

def test_non_empty_returns_list_when_non_empty():
    lst = [1, 2, 3]
    assert compose(lst, collections.non_empty) == [1, 2, 3]


def test_non_empty_returns_same_list_object():
    lst = [1, 2, 3]
    assert compose(lst, collections.non_empty) is lst


def test_non_empty_returns_none_for_empty_list():
    assert compose([], collections.non_empty) is None


def test_non_empty_short_circuits_on_none_input():
    assert compose(None, collections.non_empty) is None


def test_non_empty_single_element_list():
    assert compose([42], collections.non_empty) == [42]


def test_non_empty_in_pipeline():
    result = compose([1, 2, 3], collections.non_empty, collections.first)  # type: ignore[arg-type]
    assert result == 1


def test_non_empty_pipeline_short_circuits_on_empty():
    called = []
    result = compose([], collections.non_empty, lambda x: called.append(x) or x)
    assert result is None
    assert called == []
