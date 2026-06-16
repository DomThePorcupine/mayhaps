# mayhaps

A composable pipeline for Python. Pass a value into a chain of steps — the first failure short-circuits everything after it and raises the right error automatically.

Built to clean up FastAPI endpoints. Works anywhere.

```
pip install mayhaps
```

---

## The pitch

Real FastAPI endpoints accumulate. A handler that fetches a record, checks a few things, and saves a change ends up looking like this:

<table>
<tr>
<th width="50%">Typical Python</th>
<th width="50%">Mayhaps pipeline</th>
</tr>
<tr>
<td valign="top">

```python
@router.patch("/posts/{post_id}/publish")
def publish_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )
    if post.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Not your post",
        )
    if post.status == "published":
        raise HTTPException(
            status_code=409,
            detail="Already published",
        )
    post.status = "published"
    post.published_at = datetime.utcnow()
    db.flush()
    return post
```

</td>
<td valign="top">

```python
@router.patch("/posts/{post_id}/publish")
def publish_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return (
        HttpPipeline(post_id)
        .then(fetch_by_id(Post, db))
        .require(
            lambda p: p.author_id == user.id,
            HttpErr("Not your post", status=403),
        )
        .require(
            lambda p: p.status != "published",
            HttpErr("Already published", status=409),
        )
        .tap(lambda p: setattr(p, "status", "published"))
        .tap(lambda p: setattr(p, "published_at", datetime.utcnow()))
        .then(flush(db))
    ).run()
```

</td>
</tr>
</table>

The logic is identical. But the pipeline version is a list of *what* happens, not a maze of *what to do when it doesn't*. Each step carries its own error; failures propagate automatically; `.run()` either returns the final value or raises `HTTPException`.

---

## Why composition matters

The imperative version has a hidden structure: each line only runs if the line before it succeeded. You're building a sequential pipeline by hand, one `if` at a time.

Making that structure explicit — a chain of steps where failure short-circuits — is the core idea behind the Maybe monad. Mayhaps gives you that structure without the abstraction overhead. You write functions that return `Ok(value)` or `Err(detail)`, chain them with `.then()`, and let the pipeline handle the rest.

The payoff compounds as endpoints grow. Adding a step is one line. Removing one is one line. The error path is always the same: if a step fails, `.run()` raises and nothing after it executes.

---

## HttpPipeline

`HttpPipeline` is the FastAPI-specific version. It raises `HTTPException` on failure.

```python
from mayhaps.fastapi import HttpPipeline, HttpErr, Ok, Err
```

### Methods

**`.then(fn)`** — apply `fn` to the current value. `fn` must return `Ok(value)` or an `Err`. On `Err`, the pipeline short-circuits.

```python
def get_user(db: Session) -> Callable[[int], Ok[User] | DbErr]:
    def step(user_id: int) -> Ok[User] | DbErr:
        user = db.get(User, user_id)
        return Ok(user) if user else DbErr("User not found", kind=DbErrKind.NOT_FOUND)
    return step

HttpPipeline(user_id).then(get_user(db))
```

**`.require(predicate, err)`** — guard the current value. If `predicate` returns `False`, short-circuit with `err`. Pass a plain string for a 400; pass `HttpErr` for any other status.

```python
.require(lambda u: u.is_active, "Account is deactivated")          # → 400
.require(lambda u: u.role == "admin", HttpErr("Forbidden", status=403))  # → 403
```

**`.tap(fn)`** — call `fn` for side effects without changing the pipeline value. Good for mutations before a flush.

```python
.tap(lambda u: setattr(u, "name", body.name))
```

**`.map(fn)`** — transform the value with a plain function that cannot fail.

```python
.map(lambda u: UserResponse.model_validate(u))
```

**`.run()`** — execute the pipeline. Returns the final value on success, raises `HTTPException` on failure.

**`.result()`** — returns `Ok[T] | Err` without raising. Useful when you want to inspect or branch on the outcome yourself.

### Error → status code mapping

| Error type | Status |
|---|---|
| `HttpErr(detail, status=N)` | N |
| `DbErr(kind=NOT_FOUND)` | 404 |
| `DbErr(kind=CONFLICT)` | 409 |
| `DbErr(kind=PERMISSION_DENIED)` | 403 |
| `DbErr(kind=INVALID)` | 422 |
| `Err(detail)` | 500 |

---

## SQLAlchemy helpers

Drop-in step factories for common database operations.

```python
from mayhaps.sqlalchemy import fetch_by_id, fetch_by, require_absent, save, flush
```

**`fetch_by_id(model, session)`** — look up by primary key. Returns `DbErr(NOT_FOUND)` if missing.

```python
HttpPipeline(user_id).then(fetch_by_id(User, db))
```

**`fetch_by(model, session, column)`** — look up by any column. Returns `DbErr(NOT_FOUND)` if missing.

```python
HttpPipeline(email).then(fetch_by(User, db, User.email))
```

**`require_absent(model, session, column)`** — pass through if *no* row matches. Returns `DbErr(CONFLICT)` if one exists. Useful before creating a record.

```python
HttpPipeline(body.email)
    .then(require_absent(User, db, User.email))   # 409 if email taken
    .map(lambda email: User(email=email))
    .then(save(db))
```

**`save(session)`** — `session.add(obj)` + `session.flush()`. Converts `IntegrityError` to `DbErr(CONFLICT)`.

```python
.then(save(db))
```

**`flush(session)`** — flush pending changes, passing the object through unchanged.

```python
.tap(lambda u: setattr(u, "verified", True))
.then(flush(db))
```

---

## A complete example

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mayhaps.fastapi import HttpPipeline, HttpErr, Ok, Err
from mayhaps.sqlalchemy import fetch_by_id, require_absent, save, flush

router = APIRouter()

@router.post("/users")
def create_user(body: CreateUserBody, db: Session = Depends(get_db)):
    return (
        HttpPipeline(body.email)
        .then(require_absent(User, db, User.email, detail="Email already registered"))
        .map(lambda email: User(email=email, name=body.name))
        .then(save(db))
        .map(UserResponse.model_validate)
    ).run()


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UpdateUserBody, db: Session = Depends(get_db)):
    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .require(lambda u: u.is_active, "Account is deactivated")
        .tap(lambda u: u.apply(body))
        .then(flush(db))
        .map(UserResponse.model_validate)
    ).run()


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .require(lambda u: u.id == actor.id, HttpErr("Cannot delete another user", status=403))
        .tap(db.delete)
        .then(flush(db))
    ).run()
```

---

## Result types

```python
from mayhaps.fastapi import Ok, Err, HttpErr, DbErr, DbErrKind
```

| Type | Purpose |
|---|---|
| `Ok(value)` | Successful step result |
| `Err(detail)` | Generic failure |
| `HttpErr(detail, status=N)` | HTTP failure with an explicit status code |
| `DbErr(detail, kind=K)` | Database failure; `kind` maps to an HTTP status automatically |

Write your own step factories the same way the built-ins do:

```python
def check_quota(db: Session) -> Callable[[User], Ok[User] | HttpErr]:
    def step(user: User) -> Ok[User] | HttpErr:
        if user.api_calls_this_month >= user.plan.limit:
            return HttpErr("Rate limit exceeded", status=429)
        return Ok(user)
    return step
```

---

## compose — lightweight Maybe monad

For cases where you don't need error details, `compose` threads a value through functions that return `None` on failure:

```python
from mayhaps import compose

result = compose(
    raw_value,
    parse_int,        # returns int | None
    positive,         # returns int | None
    str,              # plain transform
)
# result is int | None
```

Returns `None` the moment any step returns `None` (or if the input is `None`). Every function receives the output of the previous one.

---

## Pipeline — framework-agnostic

`Pipeline` works the same as `HttpPipeline` but raises `MayhapsError` instead of `HTTPException`. Use it outside of FastAPI:

```python
from mayhaps import Pipeline
from mayhaps.result import Ok, Err

result = (
    Pipeline(user_id)
    .then(load_user)
    .require(lambda u: u.is_active, Err("Inactive"))
    .map(serialize)
).run()  # raises MayhapsError on failure
```
