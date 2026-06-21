import time
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from models import get_session, CsrfToken
from session_utils import generate_session_token, hash_token


CSRF_COOKIE_NAME = "__Host-csrf"


def generate_csrf_token(session_id: int) -> str:
    raw_token = generate_session_token()
    token_hash_val = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    sess = get_session()
    try:
        csrf = CsrfToken(
            session_id=session_id,
            token_hash=token_hash_val,
            expires_at=expires_at,
        )
        sess.add(csrf)
        sess.commit()
        return raw_token
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


def verify_csrf(request: Request, form_token: str) -> bool:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token or not form_token:
        return False
    # Constant-time comparison
    return cookie_token == form_token


def inject_csrf(response: Response, csrf_token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=False,  # Set True in production via config
        samesite="lax",
        path="/",
        max_age=86400,  # 24 hours
    )
