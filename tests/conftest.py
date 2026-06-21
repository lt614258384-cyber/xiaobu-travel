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

    # Reset in-memory rate limit buckets so tests don't interfere
    from middleware import rate_limit
    rate_limit._ip_buckets.clear()
    rate_limit._user_buckets.clear()

    yield


@pytest.fixture
def registered_user():
    """Creates a test user and returns (client, email, password, user_id)."""
    from fastapi.testclient import TestClient
    from models import get_session, init_db, User
    from crypto_utils import hash_password
    from app import app

    # Ensure tables exist in the isolated test database
    init_db()

    sess = get_session()
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        pet_name="TestDog",
        is_admin=False,
    )
    sess.add(user)
    sess.commit()
    user_id = user.id
    sess.close()

    client = TestClient(app, follow_redirects=False)
    return client, "test@example.com", "testpass123", user_id


@pytest.fixture
def authenticated_client(registered_user):
    """Returns a TestClient that is already logged in, with CSRF token available.

    Returns (client, user_id, csrf_token).
    The client has __Host-sid and __Host-csrf cookies set.
    Use csrf_token as the _csrf_token form field value for POST requests.
    """
    from middleware.auth import SESSION_COOKIE_NAME
    from middleware.csrf import CSRF_COOKIE_NAME

    client, email, password, user_id = registered_user
    resp = client.post("/login", data={
        "email": email,
        "password": password,
        "remember_me": "false",
    })
    assert resp.status_code == 303, f"Login failed: status {resp.status_code}"

    # Extract cookies from the login response
    session_token = resp.cookies.get(SESSION_COOKIE_NAME)
    csrf_token_cookie = resp.cookies.get(CSRF_COOKIE_NAME)

    assert session_token is not None, (
        f"Session cookie '{SESSION_COOKIE_NAME}' not set in login response"
    )
    assert csrf_token_cookie is not None, (
        f"CSRF cookie '{CSRF_COOKIE_NAME}' not set in login response"
    )

    # Set cookies on the test client for subsequent requests
    client.cookies.set(SESSION_COOKIE_NAME, session_token)
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token_cookie)

    return client, user_id, csrf_token_cookie
