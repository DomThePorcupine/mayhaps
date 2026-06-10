from dataclasses import dataclass

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from mayhaps.fastapi import Err, Ok, Pipeline


# --- domain models -----------------------------------------------------------

@dataclass
class User:
    id: int
    name: str
    org_id: int
    is_active: bool


@dataclass
class Profile:
    user_id: int
    bio: str


# --- fake database -----------------------------------------------------------

USERS: dict[int, User] = {
    1: User(id=1, name="Alice", org_id=10, is_active=True),
    2: User(id=2, name="Bob",   org_id=10, is_active=False),
    3: User(id=3, name="Carol", org_id=99, is_active=True),
}

PROFILES: dict[int, Profile] = {
    1: Profile(user_id=1, bio="Engineer"),
}


# --- pipeline steps ----------------------------------------------------------

def fetch_user(user_id: int) -> Ok[User] | Err:
    user = USERS.get(user_id)
    return Ok(user) if user else Err(404, "User not found")


def check_org(user: User) -> Ok[User] | Err:
    return Ok(user) if user.org_id == 10 else Err(403, "Access denied")


def check_active(user: User) -> Ok[User] | Err:
    return Ok(user) if user.is_active else Err(422, "User is deactivated")


def fetch_profile(user: User) -> Ok[Profile] | Err:
    profile = PROFILES.get(user.id)
    return Ok(profile) if profile else Err(404, "Profile not found")


def exploding_step(user: User) -> Ok[User] | Err:
    raise RuntimeError("database connection lost")


def http_exception_step(user: User) -> Ok[User] | Err:
    raise HTTPException(status_code=503, detail="upstream unavailable")


# --- app & routes ------------------------------------------------------------

app = FastAPI()


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict[str, int | str]:
    user = (
        Pipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .run()
    )
    return {"id": user.id, "name": user.name}


@app.get("/users/{user_id}/profile")
def get_user_profile(user_id: int) -> dict[str, str]:
    profile = (
        Pipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .then(fetch_profile)
        .run()
    )
    return {"bio": profile.bio}


@app.get("/users/{user_id}/explode")
def get_user_explode(user_id: int) -> dict[str, int]:
    result = (
        Pipeline(user_id)
        .then(fetch_user)
        .then(exploding_step)
        .run()
    )
    return {"id": result.id}


@app.get("/users/{user_id}/http-exception")
def get_user_http_exception(user_id: int) -> dict[str, int]:
    result = (
        Pipeline(user_id)
        .then(fetch_user)
        .then(http_exception_step)
        .run()
    )
    return {"id": result.id}


client = TestClient(app, raise_server_exceptions=False)
