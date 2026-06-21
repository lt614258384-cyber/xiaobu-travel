import os
import tempfile
from pathlib import Path

import pytest

from config import settings


@pytest.fixture(autouse=True)
def isolated_test_db(monkeypatch, tmp_path):
    """Ensure every test uses an isolated SQLite database."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    # Use fake image generator in tests to avoid API calls
    monkeypatch.setattr(settings, "IMAGE_API_TYPE", "fake")
    yield
