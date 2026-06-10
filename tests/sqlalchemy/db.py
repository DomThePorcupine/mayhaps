import pytest
from sqlalchemy import Boolean, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    published: Mapped[bool] = mapped_column(Boolean, default=False)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as sess:
        yield sess
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def alice(session: Session) -> User:
    user = User(id=1, name="Alice", email="alice@example.com", is_active=True)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def bob(session: Session) -> User:
    user = User(id=2, name="Bob", email="bob@example.com", is_active=False)
    session.add(user)
    session.flush()
    return user
