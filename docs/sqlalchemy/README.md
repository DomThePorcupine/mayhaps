# mayhaps.sqlalchemy

SQLAlchemy step factories for use with `HttpPipeline` (FastAPI routes) or the core `Pipeline` (scripts and background workers).

## Install

```
pip install mayhaps[sqlalchemy]
# For FastAPI routes, also install mayhaps[fastapi]
```

## Error kinds

Helpers return `DbErr` — a subclass of `Err` that carries a semantic `kind` instead of an HTTP status code.
`HttpPipeline` converts `DbErr` to `HTTPException` automatically using sensible defaults:

| `DbErrKind`        | HTTP status |
|--------------------|-------------|
| `NOT_FOUND`        | 404         |
| `CONFLICT`         | 409         |
| `PERMISSION_DENIED`| 403         |
| `INVALID`          | 422         |

Steps you write yourself can return `HttpErr` directly when you need a specific status that doesn't fit a semantic kind.

## Helpers

Each helper is a step factory — it returns a callable that accepts the current pipeline value and returns `Ok[T] | DbErr`.

### `fetch_by_id`

Look up a row by primary key. Returns `DbErr(kind=NOT_FOUND)` if not found.

```python
from mayhaps.sqlalchemy import fetch_by_id

HttpPipeline(user_id).then(fetch_by_id(User, db)).run()
```

Optional kwarg: `detail` (default `"{ModelName} not found"`).

### `fetch_by`

Look up a row by any column. Returns `DbErr(kind=NOT_FOUND)` if not found.

```python
from mayhaps.sqlalchemy import fetch_by

HttpPipeline(email).then(fetch_by(User, db, User.email)).run()
```

Optional kwarg: `detail`.

### `require`

Guard step: pass through if a predicate holds, otherwise short-circuit with `DbErr`.

```python
from mayhaps.result import DbErrKind
from mayhaps.sqlalchemy import require

check_active = require(lambda u: u.is_active,    kind=DbErrKind.INVALID,           detail="User is deactivated")
check_admin  = require(lambda u: u.role == "admin", kind=DbErrKind.PERMISSION_DENIED, detail="Admin only")
```

### `require_absent`

Uniqueness check: pass through if no row matches `column == value`, otherwise short-circuit with `DbErr(kind=CONFLICT)`.

```python
from mayhaps.sqlalchemy import require_absent

HttpPipeline(email)
    .then(require_absent(User, db, User.email, detail="Email already registered"))
    .then(lambda e: Ok(User(email=e, ...)))
    .then(save(db))
    .run()
```

### `save`

Add the object to the session and flush. Converts `IntegrityError` to `DbErr(kind=CONFLICT)` so concurrent uniqueness races are handled gracefully.

```python
from mayhaps.sqlalchemy import save

.then(save(db))
.then(save(db, conflict_detail="Username already taken"))
```

## Using with core `Pipeline` (scripts)

The helpers work equally well outside of FastAPI. Use `Pipeline` from `mayhaps` and catch `MayhapsError`. The `kind` field is preserved so scripts can branch on it if needed:

```python
from mayhaps import MayhapsError, Pipeline
from mayhaps.result import DbErrKind
from mayhaps.sqlalchemy import fetch_by_id, require

try:
    user = (
        Pipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(require(lambda u: u.is_active, kind=DbErrKind.INVALID, detail="Inactive"))
        .run()
    )
except MayhapsError as e:
    if e.kind == DbErrKind.NOT_FOUND:
        print("User does not exist")
    else:
        print(f"Error: {e.detail}")
```

## Extended example

See [`docs/sqlalchemy/example.py`](example.py) for a complete FastAPI + SQLAlchemy app covering read, create, and update routes.
