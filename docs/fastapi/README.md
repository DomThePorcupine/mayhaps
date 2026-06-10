# mayhaps.fastapi

A FastAPI integration that replaces the `fetch → check → raise` boilerplate in GET routes with a typed pipeline.

## Install

```
pip install mayhaps[fastapi]
```

## The problem

A typical safe GET route repeats the same pattern several times — fetch something, check if it exists, raise if not:

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = db.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not user.is_active:
        raise HTTPException(status_code=422, detail="User is deactivated")

    profile = db.get_profile(user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return UserResponse(id=user.id, name=user.name, avatar=profile.avatar_url)
```

The happy path is buried. Each step is coupled to FastAPI via `HTTPException`.

## The solution

Each step returns `Ok(value)` or `HttpErr(detail, status=...)`. `HttpPipeline` threads the value through, raising `HTTPException` automatically on the first `HttpErr`:

```python
from mayhaps.fastapi import HttpErr, HttpPipeline, Ok

def fetch_user(user_id: int) -> Ok[User] | HttpErr:
    user = db.get(user_id)
    return Ok(user) if user else HttpErr("User not found", status=404)

def check_org(user: User) -> Ok[User] | HttpErr:
    return Ok(user) if user.org_id == current_user.org_id else HttpErr("Access denied", status=403)

def check_active(user: User) -> Ok[User] | HttpErr:
    return Ok(user) if user.is_active else HttpErr("User is deactivated", status=422)

def fetch_profile(user: User) -> Ok[Profile] | HttpErr:
    profile = db.get_profile(user.id)
    return Ok(profile) if profile else HttpErr("Profile not found", status=404)

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    profile = (
        HttpPipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .then(fetch_profile)
        .run()
    )
    return UserResponse(id=profile.user_id, name=profile.name, avatar=profile.avatar_url)
```

Steps have no FastAPI imports. They're plain functions that return data — easy to test in isolation.

## Types

`HttpPipeline[T]` is fully generic. Each `.then()` call infers the output type from the step's return annotation, so the chain `HttpPipeline[int] → HttpPipeline[User] → HttpPipeline[Profile]` is tracked by the type checker end to end.

`HttpErr` is a subclass of the core `Err` type, adding a `status` field. Steps that return plain `Err` (no status) will produce a 500 if they reach `.run()`.

## Testing steps in isolation

Because steps are just functions, no FastAPI app is needed to test them:

```python
assert fetch_user(999) == HttpErr("User not found", status=404)
assert check_active(inactive_user) == HttpErr("User is deactivated", status=422)
assert check_active(active_user) == Ok(active_user)
```

## Script / non-HTTP use

For scripts or background workers, use the core `Pipeline` from `mayhaps` instead — it raises `MayhapsError` rather than `HTTPException`:

```python
from mayhaps import MayhapsError, Pipeline

try:
    user = Pipeline(user_id).then(fetch_user).run()
except MayhapsError as e:
    print(f"Error {e.status}: {e.detail}")
```
