"""
Example FastAPI server demonstrating mayhaps.fastapi.Pipeline.

Run with:
    uvicorn docs.fastapi.example:app --reload

Endpoints:
    GET /users/{user_id}         — fetch a user with profile
    GET /users/{user_id}/posts   — fetch a user's published posts
"""

from dataclasses import dataclass, field

from fastapi import FastAPI

from mayhaps.fastapi import Err, Ok, Pipeline

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

def fetch_user(user_id: int) -> Ok[User] | Err:
    user = USERS.get(user_id)
    return Ok(user) if user else Err(404, "User not found")


def check_org(user: User) -> Ok[User] | Err:
    return Ok(user) if user.org_id == CURRENT_ORG_ID else Err(403, "Access denied")


def check_active(user: User) -> Ok[User] | Err:
    return Ok(user) if user.is_active else Err(422, "User is deactivated")


def fetch_profile(user: User) -> Ok[Profile] | Err:
    profile = PROFILES.get(user.id)
    return Ok(profile) if profile else Err(404, "Profile not found")


def to_user_response(profile: Profile) -> Ok[UserResponse] | Err:
    user = USERS[profile.user_id]
    return Ok(UserResponse(id=user.id, name=user.name, avatar_url=profile.avatar_url))


def fetch_published_posts(user: User) -> Ok[UserPostsResponse] | Err:
    all_posts = POSTS.get(user.id, [])
    published = [PostSummary(id=p.id, title=p.title) for p in all_posts if p.published]
    return Ok(UserPostsResponse(user=user.name, posts=published))


# --- routes ------------------------------------------------------------------

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int) -> UserResponse:
    return (
        Pipeline(user_id)
        # int -> User
        .then(fetch_user)
        # User -> User
        .then(check_org)
        # User -> User
        .then(check_active)
        # User -> Profile
        .then(fetch_profile)
        # Profile -> UserResponse
        .then(to_user_response)
        .run()
    )


@app.get("/users/{user_id}/posts", response_model=UserPostsResponse)
def get_user_posts(user_id: int) -> UserPostsResponse:
    return (
        Pipeline(user_id)
        .then(fetch_user)
        .then(check_org)
        .then(check_active)
        .then(fetch_published_posts)
        .run()
    )
