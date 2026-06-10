# AGENTS.md

## What this project is

`mayhaps` is a small Python utility library providing a `compose` function — a practical Maybe monad for Python. It threads a value through a sequence of callables, short-circuiting to `None` the moment any step returns `None` (or the input itself is `None`).

## Key files

- `src/mayhaps/compose.py` — core `compose` function
- `src/mayhaps/converters.py` — type coercions and formatting (`to_int`, `to_float`, `to_str`, `to_percent`)
- `src/mayhaps/numeric.py` — numeric guards (`positive`, `non_negative`, `clamp`)
- `src/mayhaps/strings.py` — string validators (`non_empty`, `strip`, `matches`)
- `src/mayhaps/predicates.py` — `when` combinator

## Function signature

```python
def compose(param: T | None, *dependencies: Callable[[T], T | None]) -> T | None
```

- `param` — the initial value (may be `None`)
- `*dependencies` — zero or more single-argument callables applied in order
- Returns the transformed value, or `None` if any step (including the input) is `None`

## Behavior contract

1. If `param` is `None`, return `None` without calling any dependency.
2. Apply each dependency in order; if one returns `None`, stop and return `None`.
3. If all dependencies succeed, return the final result.

## Tests

Tests use `pytest` and are organized one file per module:

- `tests/test_compose.py`
- `tests/test_converters.py`
- `tests/test_numeric.py`
- `tests/test_strings.py`
- `tests/test_predicates.py`

Run them with:

```
uv run pytest tests/
```

Keep each test file under 300 lines. If a file approaches that limit, split it by grouping related cases into a new file.

## Development

The project uses `uv` for dependency management and packaging. Python 3.13+ is required.
