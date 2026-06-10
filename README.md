# mayhaps

`mayhaps` gives you a typed `Pipeline` that threads a value through a chain of transformations, stopping at the first failure. It removes the `if x is None: raise` ladder from your FastAPI routes and replaces it with a readable chain.

## Install

```
pip install mayhaps

# FastAPI integration
pip install mayhaps[fastapi]

# SQLAlchemy step factories
pip install mayhaps[sqlalchemy]
```

## The problem

A typical safe route repeats the same fetch-check-raise pattern over and over:

```python
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=422, detail="User is deactivated")

    profile = db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return UserResponse(id=user.id, name=user.name, avatar=profile.avatar_url)
```

The happy path is buried. Every step is coupled to FastAPI via `HTTPException`, making the logic hard to test in isolation.

## The solution

Each step returns `Ok(value)` or an error. `HttpPipeline` threads the value through, converting errors to `HTTPException` automatically:

```python
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(check_active)
        .then(fetch_profile)
        .map(to_response)
        .run()
    )
```

Steps are plain functions — no FastAPI imports, no `HTTPException`:

```python
from mayhaps.fastapi import Ok
from mayhaps.result import DbErr, DbErrKind

def check_active(user: User) -> Ok[User] | DbErr:
    return Ok(user) if user.is_active else DbErr("User is deactivated", kind=DbErrKind.INVALID)
```

And trivially testable:

```python
assert check_active(inactive_user) == DbErr("User is deactivated", kind=DbErrKind.INVALID)
assert check_active(active_user) == Ok(active_user)
```

## `Pipeline` and `HttpPipeline`

Use `.then()` for steps that can fail and `.map()` for infallible transformations:

```python
from mayhaps import Ok, Pipeline
from mayhaps.result import Err

def parse_int(s: str) -> Ok[int] | Err:
    try:
        return Ok(int(s))
    except ValueError:
        return Err("not a number")

result = (
    Pipeline("42")
    .then(parse_int)       # str → int, can fail
    .map(lambda n: n * 2)  # int → int, always succeeds
    .run()                 # returns 84, or raises MayhapsError
)
```

`HttpPipeline` is the same but `.run()` raises `HTTPException` instead of `MayhapsError`. Steps return `DbErr` with a semantic kind — no HTTP status codes in your business logic:

| `DbErrKind`         | HTTP status |
|---------------------|-------------|
| `NOT_FOUND`         | 404         |
| `CONFLICT`          | 409         |
| `PERMISSION_DENIED` | 403         |
| `INVALID`           | 422         |

Use `HttpErr(detail, status=...)` directly when you need a specific status that doesn't fit a semantic kind.

## SQLAlchemy step factories

`mayhaps.sqlalchemy` provides step factories for common database operations:

```python
from mayhaps.fastapi import HttpPipeline
from mayhaps.sqlalchemy import fetch_by_id, require_absent, save

# GET — fetch and guard
@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(check_active)
        .map(to_user_out)
        .run()
    )

# POST — uniqueness check then create
@app.post("/users", response_model=UserOut, status_code=201)
def register_user(body: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    return (
        HttpPipeline(body.email)
        .then(require_absent(User, db, User.email, detail="Email already registered"))
        .map(lambda e: User(name=body.name, email=e, is_active=True))
        .then(save(db, conflict_detail="Email already registered"))
        .map(to_user_out)
        .run()
    )

# PATCH — fetch, guard, mutate, save
@app.patch("/users/{user_id}/name", response_model=UserOut)
def rename_user(user_id: int, body: RenameRequest, db: Session = Depends(get_db)) -> UserOut:
    def apply_rename(user: User) -> Ok[User]:
        user.name = body.name
        return Ok(user)

    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(check_active)
        .then(apply_rename)
        .then(save(db))
        .map(to_user_out)
        .run()
    )
```

| Factory                                | What it does                                                    |
|----------------------------------------|-----------------------------------------------------------------|
| `fetch_by_id(Model, db)`               | Look up by primary key; `NOT_FOUND` if missing                  |
| `fetch_by(Model, db, Model.col)`       | Look up by any column; `NOT_FOUND` if missing                   |
| `require(predicate, kind=, detail=)`   | Pass through if predicate holds; short-circuit otherwise        |
| `require_absent(Model, db, Model.col)` | Short-circuit with `CONFLICT` if a matching row exists          |
| `save(db)`                             | `session.add` + flush; converts `IntegrityError` to `CONFLICT`  |

See [`docs/sqlalchemy/example.py`](docs/sqlalchemy/example.py) for a complete runnable app.
