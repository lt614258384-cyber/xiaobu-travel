from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from models import get_session, User
from crypto_utils import hash_password, verify_password
from session_utils import create_session, delete_session
from middleware.auth import _set_session_cookie, SESSION_COOKIE_NAME, COOKIE_MAX_AGE_REMEMBER, COOKIE_MAX_AGE_SESSION
from middleware.csrf import generate_csrf_token, verify_csrf
from middleware.rate_limit import check_rate_limit
from audit import log_event

templates = Jinja2Templates(directory="templates")
router = APIRouter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    pet_name: str = Form(""),
):
    ip = _client_ip(request)
    if not check_rate_limit(ip, "register", 5, 60):
        raise HTTPException(status_code=429, detail="请求太频繁，请稍后重试")

    if len(password) < 8:
        return templates.TemplateResponse(request, "register.html", {
            "request": request, "error": "邮箱或密码错误"
        })

    sess = get_session()
    try:
        existing = sess.query(User).filter_by(email=email).first()
        if existing:
            # Account enumeration prevention: same message
            log_event("user.register_attempt_exists", user_id=None, ip_address=ip,
                      user_agent=_user_agent(request))
            return templates.TemplateResponse(request, "register.html", {
                "request": request, "error": "注册成功，请登录"
            })

        password_hash = hash_password(password)
        user = User(email=email, password_hash=password_hash, pet_name=pet_name, is_admin=False)
        sess.add(user)
        sess.commit()
        sess.refresh(user)

        log_event("user.registered", user_id=user.id, ip_address=ip,
                  user_agent=_user_agent(request))
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()

    return RedirectResponse(url="/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: str = Form("false"),
):
    ip = _client_ip(request)
    if not check_rate_limit(ip, "login", 5, 60):
        raise HTTPException(status_code=429, detail="请求太频繁，请稍后重试")

    sess = get_session()
    try:
        user = sess.query(User).filter_by(email=email).first()
        if not user or not verify_password(password, user.password_hash):
            log_event("user.login_failed", user_id=user.id if user else None,
                      ip_address=ip, user_agent=_user_agent(request),
                      details={"reason": "bad_credentials"})
            return templates.TemplateResponse(request, "login.html", {
                "request": request, "error": "邮箱或密码错误"
            })

        remember = remember_me == "true"
        token, auth_session = create_session(user.id, remember, _user_agent(request))
        csrf_raw = generate_csrf_token(auth_session.id)

        log_event("user.login_success", user_id=user.id, ip_address=ip,
                  user_agent=_user_agent(request))

    finally:
        sess.close()

    max_age = COOKIE_MAX_AGE_REMEMBER if remember else COOKIE_MAX_AGE_SESSION
    response = RedirectResponse(url="/", status_code=303)
    _set_session_cookie(response, token, max_age)
    response.set_cookie(
        key="__Host-csrf",
        value=csrf_raw,
        httponly=False,  # Must be readable by JS/forms
        secure=False,  # Production: True
        samesite="lax",
        path="/",
        max_age=86400,
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.delete_cookie("__Host-csrf")
    return response
