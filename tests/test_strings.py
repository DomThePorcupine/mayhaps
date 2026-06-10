from mayhaps import compose, strings


def test_non_empty_passes():
    assert compose("hello", strings.non_empty) == "hello"


def test_non_empty_rejects_blank():
    assert compose("  ", strings.non_empty) is None


def test_non_empty_rejects_empty():
    assert compose("", strings.non_empty) is None


def test_strip_trims_whitespace():
    assert compose("  hello  ", strings.strip) == "hello"


def test_strip_rejects_whitespace_only():
    assert compose("   ", strings.strip) is None


def test_matches_passes():
    assert compose("hello-world", strings.matches(r"[a-z0-9-]+")) == "hello-world"


def test_matches_rejects():
    assert compose("Hello World", strings.matches(r"[a-z0-9-]+")) is None


def test_matches_email():
    assert compose("user@example.com", strings.matches(r"[^@]+@[^@]+\.[^@]+")) == "user@example.com"
    assert compose("not-an-email", strings.matches(r"[^@]+@[^@]+\.[^@]+")) is None
