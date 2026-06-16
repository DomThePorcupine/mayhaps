import pytest
from mayhaps import compose, env


def test_get_returns_value_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR", "hello")
    assert compose(True, env.get("TEST_VAR")) == "hello"


def test_get_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_VAR", raising=False)
    assert compose(True, env.get("TEST_VAR")) is None


def test_get_returns_none_for_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR", "")
    assert compose(True, env.get("TEST_VAR")) is None


def test_get_ignores_pipeline_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR", "value")
    assert compose("anything", env.get("TEST_VAR")) == "value"
    assert compose(42, env.get("TEST_VAR")) == "value"
    assert compose(object(), env.get("TEST_VAR")) == "value"


def test_load_returns_dict_when_all_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_URL", "postgres://localhost/db")
    monkeypatch.setenv("SECRET_KEY", "abc123")
    result = compose(True, env.load("DB_URL", "SECRET_KEY"))
    assert result == {"DB_URL": "postgres://localhost/db", "SECRET_KEY": "abc123"}


def test_load_returns_none_when_one_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_URL", "postgres://localhost/db")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert compose(True, env.load("DB_URL", "SECRET_KEY")) is None


def test_load_returns_none_when_one_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_URL", "postgres://localhost/db")
    monkeypatch.setenv("SECRET_KEY", "")
    assert compose(True, env.load("DB_URL", "SECRET_KEY")) is None


def test_load_returns_none_when_all_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert compose(True, env.load("DB_URL", "SECRET_KEY")) is None


def test_load_ignores_pipeline_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_URL", "postgres://localhost/db")
    assert compose("ignored", env.load("DB_URL")) == {"DB_URL": "postgres://localhost/db"}


def test_load_single_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINGLE", "val")
    assert compose(True, env.load("SINGLE")) == {"SINGLE": "val"}
