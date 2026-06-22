import os

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from models import get_session, User
from session_utils import validate_session, extend_session, generate_session_token


# Use __Host- prefix only on HTTPS (__Host- requires Secure=True).
# FORCE_SECURE_COOKIES=true should only be set when a TLS termination proxy
# (nginx, Caddy, Railway, etc.) is serving HTTPS in front of the app.
_IS_HTTPS = os.getenv("FORCE_SECURE_COOKIES", "").lower() in ("true", "1", "yes")
SESSION_COOKIE_NAME = "__Host-sid" if _IS_HTTPS else "sid"
COOKIE_MAX_AGE_REMEMBER = 7 * 24 * 3600  # 7 days
COOKIE_MAX_AGE_SESSION = None  # browser session


def _set_session_cookie(response: RedirectResponse, token: str, max_age: int | None) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_IS_HTTPS,
        samesite="lax",
        path="/",
        max_age=max_age,
    )


def get_current_user(request: Request) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})

    auth_session = validate_session(token)
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})

    # Try to extend
    result = extend_session(auth_session)
    if result:
        new_token, _ = result
        request.state._new_session_token = new_token

    sess = get_session()
    try:
        user = sess.get(User, auth_session.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        return user
    finally:
        sess.close()
