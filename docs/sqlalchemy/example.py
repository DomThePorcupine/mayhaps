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
from mayhaps.fastapi import HttpPipeline
from mayhaps.result import DbErr, DbErrKind
from mayhaps.sqlalchemy import fetch_by_id, require_absent, save

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

    def __init__(self, name: str, email: str, is_active: bool = True):
        self.name = name
        self.email = email
        self.is_active = is_active


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


# --- reusable steps ----------------------------------------------------------

def check_active(user: User) -> Ok[User] | DbErr:
    return Ok(user) if user.is_active else DbErr("User is deactivated", kind=DbErrKind.INVALID)


def to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email)


# --- routes ------------------------------------------------------------------

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(check_active)
        .map(to_user_out)
        .run()
    )


@app.post("/users", response_model=UserOut, status_code=201)
def register_user(body: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    return (
        HttpPipeline(body.email)
        .then(require_absent(User, db, User.email, detail="Email already registered"))
        .map(lambda email: User(name=body.name, email=email, is_active=True))
        .then(save(db, conflict_detail="Email already registered"))
        .map(to_user_out)
        .run()
    )


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
