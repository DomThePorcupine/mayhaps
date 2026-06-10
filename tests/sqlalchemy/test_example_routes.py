"""
Integration tests for the docs/sqlalchemy/example.py FastAPI app.
Uses an in-memory SQLite database via get_db override.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from docs.sqlalchemy.example import Base, User, app, get_db


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as sess:
        yield sess
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db: Session) -> TestClient:
    def override_get_db() -> Iterator[Session]:
        try:
            yield db
            db.commit()
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def alice(db: Session) -> User:
    user = User(name="Alice", email="alice@example.com", bio="Engineer", location="NYC")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def bob(db: Session) -> User:
    user = User(name="Bob", email="bob@example.com", bio="", location="", is_active=False)
    db.add(user)
    db.flush()
    return user


# --- GET /users/{user_id} ----------------------------------------------------

def test_get_user_returns_user(client: TestClient, alice: User) -> None:
    response = client.get(f"/users/{alice.id}")
    assert response.status_code == 200
    assert response.json() == {
        "id": alice.id,
        "name": "Alice",
        "email": "alice@example.com",
        "bio": "Engineer",
        "location": "NYC",
    }


def test_get_user_not_found(client: TestClient) -> None:
    response = client.get("/users/999")
    assert response.status_code == 404


def test_get_deactivated_user_returns_422(client: TestClient, bob: User) -> None:
    response = client.get(f"/users/{bob.id}")
    assert response.status_code == 422


# --- POST /users -------------------------------------------------------------

def test_register_user(client: TestClient) -> None:
    response = client.post("/users", json={"name": "Carol", "email": "carol@example.com", "bio": "Designer", "location": "LA"})
    assert response.status_code == 201
    assert response.json()["email"] == "carol@example.com"
    assert response.json()["bio"] == "Designer"


def test_register_duplicate_email_returns_409(client: TestClient, alice: User) -> None:
    response = client.post("/users", json={"name": "Dup", "email": alice.email, "bio": "", "location": ""})
    assert response.status_code == 409


# --- PATCH /users/{user_id}/name ---------------------------------------------

def test_rename_user(client: TestClient, alice: User) -> None:
    response = client.patch(f"/users/{alice.id}/name", json={"name": "Alicia"})
    assert response.status_code == 200
    assert response.json()["name"] == "Alicia"


# --- PATCH /users/{user_id} --------------------------------------------------

def test_update_user_returns_updated_fields(client: TestClient, alice: User) -> None:
    response = client.patch(f"/users/{alice.id}", json={"name": "Alicia", "bio": "Senior Engineer", "location": "SF"})
    assert response.status_code == 200
    assert response.json() == {
        "id": alice.id,
        "name": "Alicia",
        "email": "alice@example.com",
        "bio": "Senior Engineer",
        "location": "SF",
    }


def test_update_inactive_user_returns_422(client: TestClient, bob: User) -> None:
    response = client.patch(f"/users/{bob.id}", json={"name": "Bobby", "bio": "", "location": ""})
    assert response.status_code == 422


def test_update_nonexistent_user_returns_404(client: TestClient) -> None:
    response = client.patch("/users/999", json={"name": "Ghost", "bio": "", "location": ""})
    assert response.status_code == 404


# --- PATCH /users/{user_id}/email --------------------------------------------

def test_change_email_returns_updated_email(client: TestClient, alice: User) -> None:
    response = client.patch(f"/users/{alice.id}/email", json={"email": "new@example.com"})
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"


def test_change_email_to_existing_email_returns_409(client: TestClient, alice: User, bob: User) -> None:
    response = client.patch(f"/users/{alice.id}/email", json={"email": bob.email})
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already in use"
