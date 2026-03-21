"""
Unit tests for AppConfig.

Verifies correct defaults and environment variable overrides.
"""

import os

from config import AppConfig


class TestDefaults:
    def test_database_url_has_default(self):
        os.environ.pop("DATABASE_URL", None)
        config = AppConfig()
        assert config.database_url == "sqlite:///./data/tasks.db"

    def test_auto_complete_project_defaults_to_false(self):
        os.environ.pop("AUTO_COMPLETE_PROJECT", None)
        config = AppConfig()
        assert config.auto_complete_project is False


class TestEnvOverrides:
    def test_database_url_read_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/test.db")
        config = AppConfig()
        assert config.database_url == "sqlite:///./data/test.db"

    def test_auto_complete_project_true(self, monkeypatch):
        monkeypatch.setenv("AUTO_COMPLETE_PROJECT", "true")
        config = AppConfig()
        assert config.auto_complete_project is True

    def test_auto_complete_project_false(self, monkeypatch):
        monkeypatch.setenv("AUTO_COMPLETE_PROJECT", "false")
        config = AppConfig()
        assert config.auto_complete_project is False

    def test_auto_complete_project_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("AUTO_COMPLETE_PROJECT", "TRUE")
        config = AppConfig()
        assert config.auto_complete_project is True

    def test_auto_complete_project_mixed_case(self, monkeypatch):
        monkeypatch.setenv("AUTO_COMPLETE_PROJECT", "True")
        config = AppConfig()
        assert config.auto_complete_project is True
