from pydantic import BaseModel

from mayhaps.pipeline import Pipeline
from mayhaps.pydantic import parse
from mayhaps.result import Err, Ok, ValidationErr


class User(BaseModel):
    name: str
    age: int


# --- parse (direct step) -----------------------------------------------------

def test_parse_returns_ok_on_valid_data() -> None:
    result = parse(User)({"name": "Alice", "age": 30})
    assert result == Ok(User(name="Alice", age=30))


def test_parse_returns_validation_err_on_missing_field() -> None:
    result = parse(User)({"name": "Alice"})
    assert isinstance(result, ValidationErr)
    assert "age" in result.detail
    assert "age" in result.fields


def test_parse_returns_validation_err_on_wrong_type() -> None:
    result = parse(User)({"name": "Alice", "age": "not-a-number"})
    assert isinstance(result, ValidationErr)
    assert "age" in result.detail
    assert "age" in result.fields


def test_parse_returns_validation_err_on_empty_dict() -> None:
    result = parse(User)({})
    assert isinstance(result, ValidationErr)
    assert result.fields  # at least one field reported


def test_validation_err_is_subtype_of_err() -> None:
    result = parse(User)({})
    assert isinstance(result, Err)


# --- fields list -------------------------------------------------------------

def test_fields_contains_all_failing_paths() -> None:
    class Full(BaseModel):
        x: int
        y: int
        z: int

    result = parse(Full)({})
    assert isinstance(result, ValidationErr)
    assert set(result.fields) == {"x", "y", "z"}


def test_fields_empty_on_success() -> None:
    result = parse(User)({"name": "Bob", "age": 25})
    assert isinstance(result, Ok)


def test_nested_field_path() -> None:
    class Address(BaseModel):
        city: str

    class Person(BaseModel):
        name: str
        address: Address

    result = parse(Person)({"name": "Alice", "address": {}})
    assert isinstance(result, ValidationErr)
    assert any("address" in f for f in result.fields)


# --- integration with Pipeline.then() ----------------------------------------

def test_pipeline_parse_success() -> None:
    value = Pipeline({"name": "Alice", "age": 30}).then(parse(User)).run()
    assert value == User(name="Alice", age=30)


def test_pipeline_parse_failure_returns_validation_err() -> None:
    result = Pipeline({"name": "Alice"}).then(parse(User)).result()
    assert isinstance(result, ValidationErr)
    assert "age" in result.fields


def test_pipeline_short_circuits_before_parse() -> None:
    called = False

    def never_called(data: dict) -> Ok[User] | Err:
        nonlocal called
        called = True
        return parse(User)(data)

    result = (
        Pipeline({"name": "Bob", "age": 25})
        .then(lambda d: Err("upstream failure"))
        .then(never_called)
        .result()
    )
    assert isinstance(result, Err)
    assert result.detail == "upstream failure"
    assert not called


def test_pipeline_chained_after_parse() -> None:
    result = (
        Pipeline({"name": "Alice", "age": 42})
        .then(parse(User))
        .map(lambda u: u.name)
        .result()
    )
    assert result == Ok("Alice")
