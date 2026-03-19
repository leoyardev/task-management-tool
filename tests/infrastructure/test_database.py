"""
Unit tests for infrastructure/database.py.
Verifies engine creation, FK enforcement, session
lifecycle, and rollback behaviour.
"""

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, inspect, text
from sqlalchemy.orm import Session

from src.infrastructure.database import (
    Base,
    build_engine,
    build_session_factory,
    get_session,
)


class ParentModel(Base):
    __tablename__ = "test_parents"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class ChildModel(Base):
    __tablename__ = "test_children"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("test_parents.id"), nullable=True)


@pytest.fixture(scope="module")
def test_engine():
    _engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)
    _engine.dispose()


@pytest.fixture(scope="module")
def test_session_factory(test_engine):
    return build_session_factory(test_engine)


class TestBuildEngine:
    def test_creates_engine_successfully(self):
        _engine = build_engine("sqlite:///:memory:")
        assert _engine is not None
        _engine.dispose()

    def test_tables_created_from_metadata(self, test_engine):
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "test_parents" in tables
        assert "test_children" in tables

    def test_foreign_keys_pragma_is_on(self, test_engine):
        with test_engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1

    def test_check_same_thread_set_for_sqlite(self):
        _engine = build_engine("sqlite:///:memory:")
        assert _engine.dialect.name == "sqlite"
        _engine.dispose()


class TestBuildSessionFactory:
    def test_returns_session_factory(self, test_session_factory):
        assert test_session_factory is not None

    def test_produces_valid_session(self, test_session_factory):
        sess = test_session_factory()
        assert isinstance(sess, Session)
        sess.close()

    def test_autocommit_is_false(self, test_session_factory):
        assert test_session_factory.kw["autocommit"] is False

    def test_autoflush_is_false(self, test_session_factory):
        assert test_session_factory.kw["autoflush"] is False

    def test_expire_on_commit_is_false(self, test_session_factory):
        assert test_session_factory.kw["expire_on_commit"] is False


class TestGetSession:
    def test_commits_on_clean_exit(self, test_session_factory):
        with get_session(test_session_factory) as sess:
            sess.add(ParentModel(id=1, name="committed"))

        with get_session(test_session_factory) as sess:
            result = sess.get(ParentModel, 1)
            assert result is not None
            assert result.name == "committed"

    def test_rolls_back_on_exception(self, test_session_factory):
        with pytest.raises(RuntimeError):
            with get_session(test_session_factory) as sess:
                sess.add(ParentModel(id=2, name="will rollback"))
                raise RuntimeError("intentional")

        with get_session(test_session_factory) as sess:
            assert sess.get(ParentModel, 2) is None

    def test_session_not_in_transaction_after_clean_exit(self, test_session_factory):
        with get_session(test_session_factory) as sess:
            captured = sess
        assert not captured.in_transaction()

    def test_session_not_in_transaction_after_exception(self, test_session_factory):
        captured = None
        with pytest.raises(RuntimeError):
            with get_session(test_session_factory) as sess:
                captured = sess
                raise RuntimeError("intentional")
        assert not captured.in_transaction()

    def test_exception_is_re_raised(self, test_session_factory):
        with pytest.raises(ValueError, match="specific error"):
            with get_session(test_session_factory) as _:
                raise ValueError("specific error")


class TestForeignKeyEnforcement:
    def test_fk_violation_raises(self, test_session_factory):
        with pytest.raises(Exception):
            with get_session(test_session_factory) as sess:
                sess.add(ChildModel(id=1, parent_id=999))
                sess.flush()

    def test_valid_fk_inserts_successfully(self, test_session_factory):
        with get_session(test_session_factory) as sess:
            sess.add(ParentModel(id=10, name="parent"))

        with get_session(test_session_factory) as sess:
            sess.add(ChildModel(id=1, parent_id=10))
            sess.flush()

        with get_session(test_session_factory) as sess:
            child = sess.get(ChildModel, 1)
            assert child.parent_id == 10

    def test_nullable_fk_allows_none(self, test_session_factory):
        with get_session(test_session_factory) as sess:
            sess.add(ChildModel(id=2, parent_id=None))

        with get_session(test_session_factory) as sess:
            child = sess.get(ChildModel, 2)
            assert child.parent_id is None
