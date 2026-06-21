"""Integration tests for authenticated and unauthenticated access."""
from fastapi.testclient import TestClient


def test_index_redirects_to_login_when_unauthenticated():
    """GET / without auth should redirect to /login."""
    from app import app
    with TestClient(app) as client:
        resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_index_accessible_when_authenticated(authenticated_client):
    """GET / with valid session cookie returns 200 and shows app title."""
    client, user_id, csrf_token = authenticated_client
    resp = client.get("/")
    assert resp.status_code == 200
    assert "小布的旅行" in resp.text


def test_profile_page_redirects_to_login_when_unauthenticated():
    """GET /profile without auth should redirect to /login."""
    from app import app
    with TestClient(app) as client:
        resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_profile_page_accessible_when_authenticated(authenticated_client):
    """GET /profile with valid session cookie returns 200."""
    client, user_id, csrf_token = authenticated_client
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "档案" in resp.text


def test_profile_save_requires_auth():
    """POST /profile without auth should redirect to /login."""
    from app import app
    with TestClient(app) as client:
        resp = client.post("/profile", data={
            "name": "小布",
            "breed": "柯基",
        }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_profile_save_succeeds_when_authenticated(authenticated_client):
    """POST /profile with valid auth and CSRF token saves profile data."""
    client, user_id, csrf_token = authenticated_client
    resp = client.post("/profile", data={
        "name": "小布",
        "breed": "柯基",
        "age": 3,
        "appearance": "一只奶油色柯基，大耳朵",
        "personality_tags": '["活泼","贪吃"]',
        "interests": '["追球","晒太阳"]',
        "habits": "每天早上要散步",
        "content_preference": "caption",
        "_csrf_token": csrf_token,
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/profile"


def test_profile_save_rejected_without_csrf(authenticated_client):
    """POST /profile without _csrf_token field should get 403."""
    client, user_id, csrf_token = authenticated_client
    resp = client.post("/profile", data={
        "name": "小布",
        "breed": "柯基",
        "age": 3,
    }, follow_redirects=False)
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


def test_profile_save_rejected_with_wrong_csrf(authenticated_client):
    """POST /profile with wrong CSRF token should get 403."""
    client, user_id, csrf_token = authenticated_client
    resp = client.post("/profile", data={
        "name": "小布",
        "breed": "柯基",
        "age": 3,
        "_csrf_token": "wrong-token-value",
    }, follow_redirects=False)
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


def test_login_page_returns_200():
    """GET /login should be accessible without auth."""
    from app import app
    with TestClient(app) as client:
        resp = client.get("/login")
    assert resp.status_code == 200
    assert "邮箱" in resp.text  # login form has email field


def test_register_page_returns_200():
    """GET /register should be accessible without auth."""
    from app import app
    with TestClient(app) as client:
        resp = client.get("/register")
    assert resp.status_code == 200
