from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """
    Shared declarative base for all ORM models.
    """


def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
    """
    SQLite disables FK enforcement by default on every new connection.
    This listener re-enables it so fk_tasks_project_id is enforced.
    Without this, deleting a project would not raise even with a FK defined.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(database_url: str):
    """
    Build a SQLAlchemy engine from a database URL.
    Applies SQLite-specific configuration automatically when
    the URL starts with 'sqlite'.
    """
    connect_args = {}
    engine_kwargs = {}

    if database_url.startswith("sqlite"):
        # Required when the same connection is shared across threads
        # which FastAPI does via its dependency injection system
        connect_args["check_same_thread"] = False
        engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=False,
        **engine_kwargs,
    )

    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_foreign_keys)

    return engine


def build_session_factory(engine) -> sessionmaker:
    """
    Build a session factory bound to the given engine.

    expire_on_commit=False — keeps ORM objects usable after
    session.commit() without issuing a new SELECT.
    """
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def get_session(session_factory: sessionmaker) -> Generator[Session, None, None]:
    """
    Context manager providing a transactional session scope.

    Commits on clean exit, rolls back on any exception,
    always closes the session.

    Usage:
        with get_session(session_factory) as session:
            session.add(some_orm_object)
    """
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
