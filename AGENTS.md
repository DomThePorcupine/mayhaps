# AGENTS.md

## What this project is

`mayhaps` is a small Python utility library providing a `compose` function — a practical Maybe monad for Python. It threads a value through a sequence of callables, short-circuiting to `None` the moment any step returns `None` (or the input itself is `None`).

## Key file

- `src/mayhaps/compose.py` — the entire implementation. One function, ~10 lines.

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

Tests live in `tests/test_compose.py` and use `pytest`. Run them with:

```
uv run pytest tests/
```

## Development

The project uses `uv` for dependency management and packaging. Python 3.13+ is required.
