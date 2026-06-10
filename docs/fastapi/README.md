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

Each step returns `Ok(value)` or `Err(status, detail)`. `Pipeline` threads the value through, raising `HTTPException` automatically on the first `Err`:

```python
from mayhaps.fastapi import Ok, Err, Pipeline

def fetch_user(user_id: int) -> Ok[User] | Err:
    user = db.get(user_id)
    return Ok(user) if user else Err(404, "User not found")

def check_org(user: User) -> Ok[User] | Err:
    return Ok(user) if user.org_id == current_user.org_id else Err(403, "Access denied")

def check_active(user: User) -> Ok[User] | Err:
    return Ok(user) if user.is_active else Err(422, "User is deactivated")

def fetch_profile(user: User) -> Ok[Profile] | Err:
    profile = db.get_profile(user.id)
    return Ok(profile) if profile else Err(404, "Profile not found")

def to_response(profile: Profile) -> Ok[UserResponse] | Err:
    return Ok(UserResponse(id=profile.user_id, name=profile.name, avatar=profile.avatar_url))

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    return (
        Pipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .then(fetch_profile)
        .then(to_response)
        .run()
    )
```

Steps have no FastAPI imports. They're plain functions that return data — easy to test in isolation.

## Types

`Pipeline[T]` is fully generic. Each `.then()` call infers the output type from the step's return annotation, so the chain `Pipeline[int] → Pipeline[User] → Pipeline[Profile] → Pipeline[UserResponse]` is tracked by the type checker end to end.

## Testing steps in isolation

Because steps are just functions, no FastAPI app is needed to test them:

```python
assert fetch_user(999) == Err(404, "User not found")
assert check_active(inactive_user) == Err(422, "User is deactivated")
assert check_active(active_user) == Ok(active_user)
```
