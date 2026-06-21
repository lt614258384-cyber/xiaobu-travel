import pytest
from fastapi import FastAPI, Request, Form
from fastapi.testclient import TestClient
from fastapi.responses import HTMLResponse, JSONResponse
from middleware.csrf import generate_csrf_token, verify_csrf


def test_generate_and_verify_csrf_token(tmp_path, monkeypatch):
    """Test that generate_csrf_token produces a valid 64-char hex token."""
    from config import settings
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'csrf.db'}")
    from models import init_db
    init_db()

    token = generate_csrf_token(session_id=1)
    assert len(token) == 64

    # Since we can't easily test with actual Request object without full app,
    # test that token format is correct
    assert all(c in "0123456789abcdef" for c in token)


def test_verify_csrf_valid():
    """Test verify_csrf with matching cookie and form tokens."""
    app = FastAPI()

    @app.post("/test-csrf")
    async def test_endpoint(request: Request, csrf_token: str = Form(...)):
        valid = verify_csrf(request, csrf_token)
        if valid:
            return JSONResponse({"status": "ok"})
        return JSONResponse({"status": "bad"}, status_code=403)

    client = TestClient(app)
    response = client.post(
        "/test-csrf",
        data={"csrf_token": "test-token"},
        cookies={"__Host-csrf": "test-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_verify_csrf_missing_form_token():
    """Test verify_csrf with missing form token."""
    app = FastAPI()

    @app.post("/test-csrf")
    async def test_endpoint(request: Request, csrf_token: str = Form(...)):
        valid = verify_csrf(request, csrf_token)
        if valid:
            return JSONResponse({"status": "ok"})
        return JSONResponse({"status": "bad"}, status_code=403)

    client = TestClient(app)
    response = client.post(
        "/test-csrf",
        data={"csrf_token": "test-token"},
        # No cookie
    )
    assert response.status_code == 403


def test_verify_csrf_mismatched_token():
    """Test verify_csrf with mismatched cookie and form tokens."""
    app = FastAPI()

    @app.post("/test-csrf")
    async def test_endpoint(request: Request, csrf_token: str = Form(...)):
        valid = verify_csrf(request, csrf_token)
        if valid:
            return JSONResponse({"status": "ok"})
        return JSONResponse({"status": "bad"}, status_code=403)

    client = TestClient(app)
    response = client.post(
        "/test-csrf",
        data={"csrf_token": "correct-token"},
        cookies={"__Host-csrf": "wrong-token"},
    )
    assert response.status_code == 403
