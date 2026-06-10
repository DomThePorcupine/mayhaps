# mayhaps

Usable monads for Python. `mayhaps` gives you a `compose` function that threads a value through a chain of transformations, stopping early if any step returns `None`.

Think of it as a lightweight Maybe monad — without the ceremony.

## Install

```
pip install mayhaps
```

## Usage

```python
from mayhaps import compose
```

### Basic pipeline

```python
def parse_int(s: str) -> int | None:
    try:
        return int(s)
    except ValueError:
        return None

def double(n: int) -> int:
    return n * 2

compose("21", parse_int, double)  # 42
compose("oops", parse_int, double)  # None
```

### Short-circuiting on None input

```python
compose(None, double)  # None — dependencies are never called
```

### Chaining multiple steps

```python
def clamp(n: int) -> int | None:
    return n if 0 <= n <= 100 else None

def to_percent(n: int) -> str:
    return f"{n}%"

compose(42, double, clamp, to_percent)   # "84%"
compose(60, double, clamp, to_percent)   # None (120 is out of range)
```

## API

```python
compose(value, *fns)
```

- Starts with `value`. If it is `None`, returns `None` immediately.
- Applies each function in order. If any returns `None`, stops and returns `None`.
- Otherwise returns the final result.
