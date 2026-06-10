"""
Example FastAPI server demonstrating mayhaps.fastapi.HttpPipeline.

Run with:
    uvicorn docs.fastapi.example:app --reload

Endpoints:
    GET /users/{user_id}         — fetch a user with profile
    GET /users/{user_id}/posts   — fetch a user's published posts
"""

from dataclasses import dataclass

from fastapi import FastAPI

from mayhaps.fastapi import HttpErr, HttpPipeline, Ok

app = FastAPI()


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
    avatar_url: str


@dataclass
class Post:
    id: int
    user_id: int
    title: str
    published: bool


@dataclass
class UserResponse:
    id: int
    name: str
    avatar_url: str


@dataclass
class PostSummary:
    id: int
    title: str


@dataclass
class UserPostsResponse:
    user: str
    posts: list[PostSummary]


# --- fake database -----------------------------------------------------------

USERS: dict[int, User] = {
    1: User(id=1, name="Alice", org_id=10, is_active=True),
    2: User(id=2, name="Bob",   org_id=10, is_active=False),
    3: User(id=3, name="Carol", org_id=99, is_active=True),
}

PROFILES: dict[int, Profile] = {
    1: Profile(user_id=1, avatar_url="https://example.com/avatars/alice.png"),
    3: Profile(user_id=3, avatar_url="https://example.com/avatars/carol.png"),
}

POSTS: dict[int, list[Post]] = {
    1: [
        Post(id=101, user_id=1, title="Hello world",    published=True),
        Post(id=102, user_id=1, title="Draft thoughts", published=False),
        Post(id=103, user_id=1, title="Second post",    published=True),
    ],
    2: [],
}

CURRENT_ORG_ID = 10


# --- pipeline steps ----------------------------------------------------------

def fetch_user(user_id: int) -> Ok[User] | HttpErr:
    user = USERS.get(user_id)
    return Ok(user) if user else HttpErr("User not found", status=404)


def check_org(user: User) -> Ok[User] | HttpErr:
    return Ok(user) if user.org_id == CURRENT_ORG_ID else HttpErr("Access denied", status=403)


def check_active(user: User) -> Ok[User] | HttpErr:
    return Ok(user) if user.is_active else HttpErr("User is deactivated", status=422)


def fetch_profile(user: User) -> Ok[Profile] | HttpErr:
    profile = PROFILES.get(user.id)
    return Ok(profile) if profile else HttpErr("Profile not found", status=404)


def to_user_response(profile: Profile) -> Ok[UserResponse] | HttpErr:
    user = USERS[profile.user_id]
    return Ok(UserResponse(id=user.id, name=user.name, avatar_url=profile.avatar_url))


def fetch_published_posts(user: User) -> Ok[UserPostsResponse] | HttpErr:
    all_posts = POSTS.get(user.id, [])
    published = [PostSummary(id=p.id, title=p.title) for p in all_posts if p.published]
    return Ok(UserPostsResponse(user=user.name, posts=published))


# --- routes ------------------------------------------------------------------

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int) -> UserResponse:
    return (
        HttpPipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .then(fetch_profile)
        .then(to_user_response)
        .run()
    )


@app.get("/users/{user_id}/posts", response_model=UserPostsResponse)
def get_user_posts(user_id: int) -> UserPostsResponse:
    return (
        HttpPipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .then(fetch_published_posts)
        .run()
    )
