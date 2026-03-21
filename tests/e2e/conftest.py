"""
E2E test fixtures.

Uses a real FastAPI app with a real in-memory SQLite DB.
"""

import pytest
from fastapi.testclient import TestClient

from main import create_app  # noqa: F401
from src.adapters.api.dependencies import get_db
from src.infrastructure.database import Base, build_engine, build_session_factory


@pytest.fixture(scope="session")
def e2e_engine():
    """Real in-memory SQLite engine for e2e tests."""
    engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def e2e_session_factory(e2e_engine):
    return build_session_factory(e2e_engine)


@pytest.fixture
def e2e_client(e2e_session_factory):
    """
    TestClient with real services and real DB session.
    No mocks — full stack from HTTP to SQLite.
    Rolls back after each test via savepoint.
    """

    session = e2e_session_factory()
    session.begin_nested()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app, raise_server_exceptions=True)
    yield client

    session.rollback()
    session.close()
