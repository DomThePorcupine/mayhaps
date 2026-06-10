from dataclasses import dataclass

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from mayhaps.fastapi import HttpErr, HttpPipeline, Ok


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

def fetch_user(user_id: int) -> Ok[User] | HttpErr:
    user = USERS.get(user_id)
    return Ok(user) if user else HttpErr("User not found", status=404)


def check_org(user: User) -> Ok[User] | HttpErr:
    return Ok(user) if user.org_id == 10 else HttpErr("Access denied", status=403)


def check_active(user: User) -> Ok[User] | HttpErr:
    return Ok(user) if user.is_active else HttpErr("User is deactivated", status=422)


def fetch_profile(user: User) -> Ok[Profile] | HttpErr:
    profile = PROFILES.get(user.id)
    return Ok(profile) if profile else HttpErr("Profile not found", status=404)


def exploding_step(user: User) -> Ok[User] | HttpErr:
    raise RuntimeError("database connection lost")


def http_exception_step(user: User) -> Ok[User] | HttpErr:
    raise HTTPException(status_code=503, detail="upstream unavailable")


# --- app & routes ------------------------------------------------------------

app = FastAPI()


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict[str, int | str]:
    user = (
        HttpPipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .run()
    )
    return {"id": user.id, "name": user.name}


@app.get("/users/{user_id}/profile")
def get_user_profile(user_id: int) -> dict[str, str]:
    profile = (
        HttpPipeline(user_id)
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
        HttpPipeline(user_id)
        .then(fetch_user)
        .then(exploding_step)
        .run()
    )
    return {"id": result.id}


@app.get("/users/{user_id}/http-exception")
def get_user_http_exception(user_id: int) -> dict[str, int]:
    result = (
        HttpPipeline(user_id)
        .then(fetch_user)
        .then(http_exception_step)
        .run()
    )
    return {"id": result.id}


client = TestClient(app, raise_server_exceptions=False)
