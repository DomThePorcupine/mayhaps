"""
Example FastAPI + SQLAlchemy app demonstrating mayhaps pipelines for read,
create, and update routes.

Run with:
    uvicorn docs.sqlalchemy.example:app --reload

Endpoints:
    GET    /users/{user_id}       — fetch a single active user
    POST   /users                 — register a new user (unique email enforced)
    PATCH  /users/{user_id}/name  — rename a user
"""

from dataclasses import dataclass

from fastapi import Depends, FastAPI
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from mayhaps import Ok
from mayhaps.fastapi import HttpErr, HttpPipeline
from mayhaps.sqlalchemy import fetch_by_id, require, require_absent, save

app = FastAPI()

# --- database setup ----------------------------------------------------------

engine = create_engine("sqlite:///./example.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)


Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    finally:
        db.close()


# --- request / response models -----------------------------------------------

@dataclass
class UserOut:
    id: int
    name: str
    email: str


@dataclass
class RegisterRequest:
    name: str
    email: str


@dataclass
class RenameRequest:
    name: str


# --- routes ------------------------------------------------------------------

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    user = (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(require(lambda u: u.is_active, status=422, detail="User is deactivated"))
        .run()
    )
    return UserOut(id=user.id, name=user.name, email=user.email)


@app.post("/users", response_model=UserOut, status_code=201)
def register_user(body: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    user = (
        HttpPipeline(body.email)
        # Reject if the email is already taken
        .then(require_absent(User, db, User.email, detail="Email already registered"))
        # Build the new User object
        .then(lambda email: Ok(User(name=body.name, email=email, is_active=True)))
        # Persist — converts IntegrityError to 409 for concurrent races
        .then(save(db, conflict_detail="Email already registered"))
        .run()
    )
    return UserOut(id=user.id, name=user.name, email=user.email)


@app.patch("/users/{user_id}/name", response_model=UserOut)
def rename_user(user_id: int, body: RenameRequest, db: Session = Depends(get_db)) -> UserOut:
    user = (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(require(lambda u: u.is_active, status=422, detail="Cannot rename a deactivated user"))
        .run()
    )
    user.name = body.name
    db.flush()
    return UserOut(id=user.id, name=user.name, email=user.email)
