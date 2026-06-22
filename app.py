import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from models import get_session, Profile, init_db, JourneyState, JourneyLog, Location, User
from config import settings
from scheduler import Scheduler
from seed.prompt_cleanup import cleanup_activity_prompt_templates
from uploads import make_reference_photo_filename, validate_image_bytes
from middleware.auth import get_current_user, SESSION_COOKIE_NAME
from middleware.csrf import verify_csrf, generate_csrf_token
from crypto_utils import mask_api_key, unmask_api_key
from middleware.rate_limit import check_user_rate_limit
from routers.auth_routes import router as auth_router
from audit import log_event


_DATA_ROOT = Path("data")


def _media_path(db_path: str) -> str:
    """Convert stored DB path to the authenticated media URL path.

    DB stores:  "data/uploads/1/ref_abc.png" or "data/generated/1/xiaobu_123.png"
    Returns:    "media/uploads/1/ref_abc.png" or "media/generated/1/xiaobu_123.png"
    """
    if not db_path:
        return ""
    if db_path.startswith("data/"):
        return "media/" + db_path[5:]
    return db_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cleanup_activity_prompt_templates()
    scheduler = Scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    settings.check_production_safety()
    try:
        yield
    finally:
        scheduler.shutdown()
        app.state.scheduler = None


app = FastAPI(title="小布的旅行", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Register auth routes
app.include_router(auth_router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


def _csrf_check(request: Request):
    """Dependency that verifies CSRF token for state-changing requests."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    form_token = None
    # Will be extracted from form data in the route handler
    # We verify in each POST route
    return


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway — no auth required."""
    return {"status": "ok"}


@app.get("/media/{path:path}")
async def serve_media(
    path: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Serve user-scoped media files with authentication and access control.

    URL path format: /media/{uploads|generated}/{user_id}/{filename}
    Access: only the owning user may access their own files.
    """
    import os

    if ".." in path:
        raise HTTPException(status_code=404)

    segments = path.strip("/").split("/")
    if len(segments) < 3:
        raise HTTPException(status_code=404)

    subdir = segments[0]
    try:
        owner_id = int(segments[1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=404)

    filename = "/".join(segments[2:])
    if not filename:
        raise HTTPException(status_code=404)

    if subdir not in ("uploads", "generated"):
        raise HTTPException(status_code=404)

    if owner_id != current_user.id:
        raise HTTPException(status_code=403)

    file_path = (_DATA_ROOT / subdir / str(owner_id) / filename).resolve()
    safe_root = _DATA_ROOT.resolve()

    if not str(file_path).startswith(str(safe_root) + os.sep):
        raise HTTPException(status_code=404)

    if not file_path.is_file():
        raise HTTPException(status_code=404)

    return FileResponse(file_path)


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user: User = Depends(get_current_user)):
    sess = get_session()
    profile = sess.query(Profile).filter_by(user_id=current_user.id).first()
    sess.close()
    # Decrypt API keys for display
    if profile:
        profile.image_api_key = unmask_api_key(profile.image_api_key)
        profile.text_api_key = unmask_api_key(profile.text_api_key)
    photos = [_media_path(p) for p in (profile.reference_photos or [])] if profile else []
    return templates.TemplateResponse(request, "profile.html", {
        "profile": profile, "user": current_user, "photos": photos,
    })


@app.post("/profile")
async def profile_save(
    request: Request,
    current_user: User = Depends(get_current_user),
    name: str = Form("小布"),
    breed: str = Form(""),
    age: int = Form(0),
    appearance: str = Form(""),
    personality_tags: str = Form("[]"),
    interests: str = Form("[]"),
    habits: str = Form(""),
    content_preference: str = Form("caption"),
    api_provider: str = Form("volcano"),
    image_api_key: str = Form(""),
    text_api_key: str = Form(""),
    real_life_memories: str = Form(""),
    csrf_token: str = Form(None, alias="_csrf_token"),
    photos: list[UploadFile] = File([]),
):
    # CSRF check
    if not verify_csrf(request, csrf_token or ""):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    sess = get_session()
    profile = sess.query(Profile).filter_by(user_id=current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        sess.add(profile)

    profile.name = name
    # Sync pet name to User model for use in templates
    current_user.pet_name = name
    sess.add(current_user)
    profile.breed = breed
    profile.age = age
    profile.appearance = appearance
    profile.personality_tags = json.loads(personality_tags) if personality_tags else []
    profile.interests = json.loads(interests) if interests else []
    profile.habits = habits
    profile.content_preference = content_preference
    profile.api_provider = api_provider
    profile.image_api_key = mask_api_key(image_api_key) if image_api_key else ""
    profile.text_api_key = mask_api_key(text_api_key) if text_api_key else ""
    profile.real_life_memories = real_life_memories

    # Upload with user-scoped directory
    existing = profile.reference_photos or []
    photo_paths = list(existing)
    for photo in photos:
        if photo.filename and photo.size > 0:
            if len(photo_paths) >= settings.MAX_REFERENCE_PHOTOS:
                break
            filename = make_reference_photo_filename(photo.filename)
            # Read and validate image bytes
            contents = await photo.read()
            suffix = Path(photo.filename).suffix.lower()
            validate_image_bytes(contents, suffix)
            # Write validated file
            user_upload_dir = settings.UPLOAD_DIR / str(current_user.id)
            user_upload_dir.mkdir(parents=True, exist_ok=True)
            filepath = user_upload_dir / filename
            with open(filepath, "wb") as file_handle:
                file_handle.write(contents)
            photo_paths.append(f"data/uploads/{current_user.id}/{filename}")

    profile.reference_photos = photo_paths[:settings.MAX_REFERENCE_PHOTOS]
    sess.commit()

    log_count = sess.query(JourneyLog).filter_by(user_id=current_user.id).count()
    sess.close()
    if log_count == 0:
        import threading
        def gen_first():
            Scheduler().run_generation(current_user.id)
        t = threading.Thread(target=gen_first, daemon=True)
        t.start()

    return RedirectResponse(url="/profile", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: User = Depends(get_current_user)):
    sess = get_session()
    state = sess.query(JourneyState).filter_by(user_id=current_user.id).first()
    logs = sess.query(JourneyLog).filter_by(user_id=current_user.id).order_by(JourneyLog.generated_at.desc()).all()

    location = None
    if state and state.current_location_id:
        location = sess.get(Location,state.current_location_id)

    enriched = []
    for log in logs:
        loc_name = ""
        if log.location_id:
            loc = sess.get(Location,log.location_id)
            loc_name = loc.name if loc else ""
        enriched.append({
            "id": log.id, "location_name": loc_name,
            "story_text": log.story_text, "image_path": _media_path(log.image_path),
            "weather": log.weather, "mood": log.mood,
            "generated_at": log.generated_at,
        })

    sess.close()
    return templates.TemplateResponse(request, "index.html", {
        "request": request, "state": state, "location": location, "logs": enriched, "user": current_user,
    })


@app.get("/api/latest")
async def api_latest(request: Request, current_user: User = Depends(get_current_user)):
    """Return the latest journey log as JSON for polling after generation."""
    sess = get_session()
    log = (
        sess.query(JourneyLog)
        .filter_by(user_id=current_user.id)
        .order_by(JourneyLog.generated_at.desc())
        .first()
    )
    if not log:
        sess.close()
        return {"id": 0, "story_text": "", "image_path": "", "location_name": "", "weather": "", "mood": ""}

    loc_name = ""
    if log.location_id:
        loc = sess.get(Location,log.location_id)
        loc_name = loc.name if loc else ""
    sess.close()
    return {
        "id": log.id,
        "story_text": log.story_text or "",
        "image_path": _media_path(log.image_path or ""),
        "location_name": loc_name,
        "weather": log.weather or "",
        "mood": log.mood or "",
        "generated_at": log.generated_at.strftime("%m月%d日 %H:%M") if log.generated_at else "",
    }


@app.get("/mailbox", response_class=HTMLResponse)
async def mailbox_page(request: Request, current_user: User = Depends(get_current_user)):
    sess = get_session()
    logs = (
        sess.query(JourneyLog)
        .filter_by(user_id=current_user.id)
        .order_by(JourneyLog.generated_at.desc())
        .all()
    )

    enriched = []
    for log in logs:
        loc_name = ""
        if log.location_id:
            loc = sess.get(Location,log.location_id)
            loc_name = loc.name if loc else ""
        enriched.append({
            "id": log.id,
            "location_name": loc_name,
            "story_text": log.story_text,
            "image_path": _media_path(log.image_path),
            "weather": log.weather,
            "mood": log.mood,
            "generated_at": log.generated_at,
        })

    sess.close()
    return templates.TemplateResponse(request, "mailbox.html", {
        "logs": enriched, "user": current_user,
    })


@app.get("/letter/{log_id}", response_class=HTMLResponse)
async def letter_detail(log_id: int, request: Request, current_user: User = Depends(get_current_user)):
    sess = get_session()
    log = sess.query(JourneyLog).filter_by(id=log_id, user_id=current_user.id).first()
    if not log:
        sess.close()
        raise HTTPException(status_code=404, detail="Letter not found")

    loc_name = ""
    if log.location_id:
        loc = sess.get(Location,log.location_id)
        loc_name = loc.name if loc else ""

    sess.close()
    return templates.TemplateResponse(request, "letter.html", {
        "letter": {
            "id": log.id,
            "location_name": loc_name,
            "story_text": log.story_text,
            "image_path": _media_path(log.image_path),
            "weather": log.weather,
            "mood": log.mood,
            "generated_at": log.generated_at,
        },
        "user": current_user,
    })


@app.post("/generate")
async def generate_now(request: Request, current_user: User = Depends(get_current_user),
                       csrf_token: str = Form(None, alias="_csrf_token")):
    # CSRF check
    if not verify_csrf(request, csrf_token or ""):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    # Rate limit check
    if not check_user_rate_limit(current_user.id, "generate", 10, 86400):
        raise HTTPException(status_code=429, detail="今天生成次数已达上限")

    log_event("generate.requested", user_id=current_user.id,
              ip_address=request.client.host if request.client else "",
              user_agent=request.headers.get("user-agent", ""))

    # Try to consume from buffer first
    scheduler = Scheduler()
    result = scheduler.consume_buffer(current_user.id)
    if result:
        # Also kick off background refill if needed
        import threading
        t = threading.Thread(target=scheduler.refill_buffer, args=(current_user.id,), daemon=True)
        t.start()
        return {"status": "ok", "message": "Consumed from buffer"}

    # Buffer empty — fall back to direct generation
    import threading
    def gen():
        Scheduler().run_generation(current_user.id)
    t = threading.Thread(target=gen, daemon=True)
    t.start()
    return {"status": "ok", "message": "Generation started"}
