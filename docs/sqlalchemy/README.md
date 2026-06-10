# mayhaps.sqlalchemy

SQLAlchemy step factories for use with `HttpPipeline` (FastAPI routes) or the core `Pipeline` (scripts and background workers).

## Install

```
pip install mayhaps[sqlalchemy]
# For FastAPI routes, also install mayhaps[fastapi]
```

## Helpers

Each helper is a step factory — it returns a callable that accepts the current pipeline value and returns `Ok[T] | HttpErr`.

### `fetch_by_id`

Look up a row by primary key. Returns `HttpErr(status=404)` if not found.

```python
from mayhaps.sqlalchemy import fetch_by_id

def get_user(user_id: int, db: Session):
    return HttpPipeline(user_id).then(fetch_by_id(User, db)).run()
```

Optional kwargs: `status` (default 404), `detail` (default `"{ModelName} not found"`).

### `fetch_by`

Look up a row by any column. Returns `HttpErr(status=404)` if not found.

```python
from mayhaps.sqlalchemy import fetch_by

def login(email: str, db: Session):
    return HttpPipeline(email).then(fetch_by(User, db, User.email)).run()
```

Optional kwargs: `status`, `detail`.

### `require`

Guard step: pass through if a predicate holds, otherwise short-circuit with `HttpErr`.

```python
from mayhaps.sqlalchemy import require

check_active = require(lambda u: u.is_active, status=422, detail="User is deactivated")
check_admin  = require(lambda u: u.role == "admin", status=403, detail="Forbidden")
```

### `require_absent`

Uniqueness check: pass through if no row matches `column == value`, otherwise short-circuit with `HttpErr(status=409)`.

```python
from mayhaps.sqlalchemy import require_absent

def register(email: str, db: Session):
    return (
        HttpPipeline(email)
        .then(require_absent(User, db, User.email, detail="Email already registered"))
        .then(lambda e: Ok(User(email=e, ...)))
        .then(save(db))
        .run()
    )
```

### `save`

Add the object to the session and flush. Converts `IntegrityError` to `HttpErr(status=409)` so concurrent uniqueness races are handled gracefully.

```python
from mayhaps.sqlalchemy import save

.then(save(db))
.then(save(db, conflict_detail="Username already taken"))
```

## Using with core `Pipeline` (scripts)

The helpers work equally well outside of FastAPI. Use `Pipeline` from `mayhaps` and catch `MayhapsError`:

```python
from mayhaps import MayhapsError, Pipeline
from mayhaps.sqlalchemy import fetch_by_id, require

try:
    user = (
        Pipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(require(lambda u: u.is_active, status=422, detail="Inactive"))
        .run()
    )
except MayhapsError as e:
    print(f"[{e.status}] {e.detail}")
```

`MayhapsError.status` carries the same status code from `HttpErr`, so scripts can branch on it if useful.

## Extended example

See [`docs/sqlalchemy/example.py`](example.py) for a complete FastAPI + SQLAlchemy app covering read, create, and update routes.
