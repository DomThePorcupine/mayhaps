"""
Example FastAPI + SQLAlchemy app demonstrating mayhaps pipelines for read,
create, and update routes.

Run with:
    uvicorn docs.sqlalchemy.example:app --reload

Endpoints:
    GET    /users/{user_id}        — fetch a single active user
    POST   /users                  — register a new user (unique email enforced)
    PATCH  /users/{user_id}/name   — rename a user
    PATCH  /users/{user_id}        — update multiple user fields
"""

from dataclasses import dataclass

from fastapi import Depends, FastAPI
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from mayhaps.fastapi import HttpPipeline, Ok
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
    bio: Mapped[str] = mapped_column(String(500), default="")
    location: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(default=True)

    def __init__(self, name: str, email: str, bio: str = "", location: str = "", is_active: bool = True):
        self.name = name
        self.email = email
        self.bio = bio
        self.location = location
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
    bio: str
    location: str


@dataclass
class RegisterRequest:
    name: str
    email: str
    bio: str = ""
    location: str = ""


@dataclass
class RenameRequest:
    name: str


@dataclass
class UpdateRequest:
    name: str
    bio: str
    location: str


@dataclass
class ChangeEmailRequest:
    email: str


# --- reusable steps ----------------------------------------------------------

def check_active(user: User) -> Ok[User] | DbErr:
    return Ok(user) if user.is_active else DbErr("User is deactivated", kind=DbErrKind.INVALID)


def to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, bio=user.bio, location=user.location)


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
        .map(lambda e: User(name=body.name, email=e, bio=body.bio, location=body.location))
        .then(save(db, conflict_detail="Email already registered"))
        .map(to_user_out)
        .run()
    )


@app.patch("/users/{user_id}/name", response_model=UserOut)
def rename_user(user_id: int, body: RenameRequest, db: Session = Depends(get_db)) -> UserOut:
    def apply_rename(user: User) -> None:
        user.name = body.name

    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(check_active)
        .tap(apply_rename)
        .then(save(db))
        .map(to_user_out)
        .run()
    )


@app.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UpdateRequest, db: Session = Depends(get_db)) -> UserOut:
    def apply_update(user: User) -> None:
        user.name = body.name
        user.bio = body.bio
        user.location = body.location

    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(check_active)
        .tap(apply_update)
        .then(save(db))
        .map(to_user_out)
        .run()
    )


@app.patch("/users/{user_id}/email", response_model=UserOut)
def change_email(user_id: int, body: ChangeEmailRequest, db: Session = Depends(get_db)) -> UserOut:
    from sqlalchemy import select

    def check_email_available(user: User) -> Ok[User] | DbErr:
        exists = db.scalars(select(User).where(User.email == body.email)).first()
        return DbErr("Email already in use", kind=DbErrKind.CONFLICT) if exists else Ok(user)

    def apply_email(user: User) -> None:
        user.email = body.email

    return (
        HttpPipeline(user_id)
        .then(fetch_by_id(User, db))
        .then(check_active)
        .then(check_email_available)
        .tap(apply_email)
        .then(save(db, conflict_detail="Email already in use"))
        .map(to_user_out)
        .run()
    )
