# Modules

`mayhaps` ships three submodules of pipeline-ready helpers, plus `when` at the top level.

```python
from mayhaps import compose, when
from mayhaps import converters, numeric, strings
```

---

## `converters`

Type coercions and formatting. Each function accepts a loose input and returns a typed value or `None`.

```python
from mayhaps import compose, converters

compose("42", converters.to_int)           # 42
compose("3.14", converters.to_float)       # 3.14
compose("oops", converters.to_int)         # None

compose(42, converters.to_str)             # "42"
compose(85, converters.to_percent)         # "85%"
```

String-to-number parsing is the most common use — feed raw user input straight into a pipeline:

```python
compose("85", converters.to_int, numeric.clamp(0, 100), converters.to_percent)   # "85%"
compose("105", converters.to_int, numeric.clamp(0, 100), converters.to_percent)  # None
compose("abc", converters.to_int, numeric.clamp(0, 100), converters.to_percent)  # None
```

---

## `numeric`

Range and sign guards for numbers. Returns the value unchanged if it passes, `None` otherwise.

```python
from mayhaps import compose, numeric

compose(5, numeric.positive)        # 5
compose(0, numeric.positive)        # None
compose(-1, numeric.positive)       # None

compose(0, numeric.non_negative)    # 0
compose(-1, numeric.non_negative)   # None

compose(50, numeric.clamp(0, 100))  # 50
compose(150, numeric.clamp(0, 100)) # None
```

Chaining guards with parsing:

```python
compose("-5", converters.to_int, numeric.positive)     # None
compose("10", converters.to_int, numeric.positive)     # 10
compose("0", converters.to_int, numeric.non_negative)  # 0
```

---

## `strings`

Whitespace and pattern validators for strings.

```python
from mayhaps import compose, strings

compose("hello", strings.non_empty)  # "hello"
compose("  ", strings.non_empty)     # None
compose("", strings.non_empty)       # None

compose("  hello  ", strings.strip)  # "hello"
compose("   ", strings.strip)        # None
```

`strings.matches` validates a string against a regex pattern:

```python
compose("hello-world", strings.matches(r"[a-z0-9-]+"))          # "hello-world"
compose("Hello World", strings.matches(r"[a-z0-9-]+"))          # None

compose("user@example.com", strings.matches(r"[^@]+@[^@]+\.[^@]+"))  # "user@example.com"
compose("not-an-email", strings.matches(r"[^@]+@[^@]+\.[^@]+"))      # None
```

Cleaning and validating form input in one pipeline:

```python
def normalize(s: str) -> str:
    return s.lower()

compose("  Hello  ", strings.strip, normalize, strings.matches(r"[a-z]+"))    # "hello"
compose("  Hello123  ", strings.strip, normalize, strings.matches(r"[a-z]+")) # None
compose("   ", strings.strip, normalize, strings.matches(r"[a-z]+"))          # None
```

---

## `when`

`when` wraps any boolean predicate into a pipeline step. It's the escape hatch for validation logic not covered by the built-in modules.

```python
from mayhaps import compose, when

compose(4, when(lambda n: n % 2 == 0))  # 4
compose(3, when(lambda n: n % 2 == 0))  # None
```

Named predicates work too:

```python
def is_weekday(day: str) -> bool:
    return day in {"Mon", "Tue", "Wed", "Thu", "Fri"}

compose("Mon", when(is_weekday))  # "Mon"
compose("Sat", when(is_weekday))  # None
```

Mixing `when` with other modules:

```python
compose(
    "  42  ",
    strings.strip,
    converters.to_int,
    numeric.clamp(0, 100),
    when(lambda n: n % 2 == 0),
    converters.to_percent,
)
# "42%"  — stripped, parsed, in range, and even
```
