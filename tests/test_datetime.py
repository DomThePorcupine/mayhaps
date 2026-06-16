from datetime import datetime, timedelta

from mayhaps import compose, dt


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------


def test_parse_date_valid_iso():
    result = compose("2024-01-15", dt.parse_date("%Y-%m-%d"))  # type: ignore[arg-type]
    assert result == datetime(2024, 1, 15)


def test_parse_date_valid_with_time():
    result = compose("2024-06-01 12:30:00", dt.parse_date("%Y-%m-%d %H:%M:%S"))  # type: ignore[arg-type]
    assert result == datetime(2024, 6, 1, 12, 30, 0)


def test_parse_date_invalid_format():
    assert compose("not-a-date", dt.parse_date("%Y-%m-%d")) is None  # type: ignore[arg-type]


def test_parse_date_wrong_format():
    # Value looks date-like but doesn't match the given format
    assert compose("01/15/2024", dt.parse_date("%Y-%m-%d")) is None  # type: ignore[arg-type]


def test_parse_date_empty_string():
    assert compose("", dt.parse_date("%Y-%m-%d")) is None  # type: ignore[arg-type]


def test_parse_date_none_input():
    assert compose(None, dt.parse_date("%Y-%m-%d")) is None  # type: ignore[arg-type]


def test_parse_date_chained_with_pipeline():
    # Verify the returned callable works seamlessly in a compose chain
    raw = "2024-03-20"
    parsed = compose(raw, dt.parse_date("%Y-%m-%d"))  # type: ignore[arg-type]
    assert parsed == datetime(2024, 3, 20)


# ---------------------------------------------------------------------------
# future
# ---------------------------------------------------------------------------


def test_future_passes_future_datetime():
    soon = datetime.now() + timedelta(seconds=60)
    assert compose(soon, dt.future) == soon


def test_future_rejects_past_datetime():
    ago = datetime.now() - timedelta(seconds=60)
    assert compose(ago, dt.future) is None


def test_future_rejects_exact_now():
    # datetime.now() called twice — the stored value will be slightly in the past
    # by the time future() runs, so it should return None.
    # We freeze a moment just before calling compose to confirm boundary behaviour.
    just_before = datetime.now() - timedelta(microseconds=1)
    assert compose(just_before, dt.future) is None


def test_future_none_input():
    assert compose(None, dt.future) is None


# ---------------------------------------------------------------------------
# past
# ---------------------------------------------------------------------------


def test_past_passes_past_datetime():
    ago = datetime.now() - timedelta(seconds=60)
    assert compose(ago, dt.past) == ago


def test_past_rejects_future_datetime():
    soon = datetime.now() + timedelta(seconds=60)
    assert compose(soon, dt.past) is None


def test_past_rejects_future():
    just_after = datetime.now() + timedelta(seconds=60)
    assert compose(just_after, dt.past) is None


def test_past_none_input():
    assert compose(None, dt.past) is None


# ---------------------------------------------------------------------------
# in_range
# ---------------------------------------------------------------------------


def test_in_range_within_bounds():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    value = datetime(2024, 6, 15)
    assert compose(value, dt.in_range(start, end)) == value


def test_in_range_at_start_bound():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    assert compose(start, dt.in_range(start, end)) == start


def test_in_range_at_end_bound():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    assert compose(end, dt.in_range(start, end)) == end


def test_in_range_before_start():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    before = datetime(2023, 12, 31)
    assert compose(before, dt.in_range(start, end)) is None


def test_in_range_after_end():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    after = datetime(2025, 1, 1)
    assert compose(after, dt.in_range(start, end)) is None


def test_in_range_none_input():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    assert compose(None, dt.in_range(start, end)) is None


# ---------------------------------------------------------------------------
# Chaining multiple datetime steps together
# ---------------------------------------------------------------------------


def test_chain_parse_and_in_range():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    result = compose("2024-06-15", dt.parse_date("%Y-%m-%d"), dt.in_range(start, end))  # type: ignore[arg-type]
    assert result == datetime(2024, 6, 15)


def test_chain_parse_and_in_range_out_of_range():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    result = compose("2025-01-01", dt.parse_date("%Y-%m-%d"), dt.in_range(start, end))  # type: ignore[arg-type]
    assert result is None


def test_chain_parse_invalid_then_in_range():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    result = compose("bad-date", dt.parse_date("%Y-%m-%d"), dt.in_range(start, end))  # type: ignore[arg-type]
    assert result is None
