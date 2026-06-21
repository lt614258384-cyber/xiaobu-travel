import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from models import get_session, Profile, init_db, JourneyState, JourneyLog, Location
from config import settings
from scheduler import Scheduler
from seed.prompt_cleanup import cleanup_activity_prompt_templates
from uploads import make_reference_photo_filename, make_reference_photo_web_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cleanup_activity_prompt_templates()
    scheduler = Scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown()
        app.state.scheduler = None


app = FastAPI(title="小布的旅行", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory="templates")


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    session = get_session()
    profile = session.query(Profile).first()
    session.close()
    return templates.TemplateResponse(request, "profile.html", {"profile": profile})


@app.post("/profile")
async def profile_save(
    request: Request,
    name: str = Form("小布"),
    breed: str = Form(""),
    age: int = Form(0),
    appearance: str = Form(""),
    personality_tags: str = Form("[]"),
    interests: str = Form("[]"),
    habits: str = Form(""),
    content_preference: str = Form("caption"),
    image_api_key: str = Form(""),
    photos: list[UploadFile] = File([]),
):
    session = get_session()
    profile = session.query(Profile).first()
    if not profile:
        profile = Profile()
        session.add(profile)

    profile.name = name
    profile.breed = breed
    profile.age = age
    profile.appearance = appearance
    profile.personality_tags = json.loads(personality_tags) if personality_tags else []
    profile.interests = json.loads(interests) if interests else []
    profile.habits = habits
    profile.content_preference = content_preference
    profile.image_api_key = image_api_key

    existing = profile.reference_photos or []
    photo_paths = list(existing)
    for photo in photos:
        if photo.filename and photo.size > 0:
            if len(photo_paths) >= settings.MAX_REFERENCE_PHOTOS:
                break
            filename = make_reference_photo_filename(photo.filename)
            filepath = settings.UPLOAD_DIR / filename
            with open(filepath, "wb") as file_handle:
                shutil.copyfileobj(photo.file, file_handle)
            photo_paths.append(make_reference_photo_web_path(filename))

    profile.reference_photos = photo_paths[:settings.MAX_REFERENCE_PHOTOS]
    session.commit()

    # If this is the first profile and no photos exist, trigger generation
    log_count = session.query(JourneyLog).count()
    session.close()
    if log_count == 0:
        import threading
        def gen_first():
            Scheduler().run_generation()
        t = threading.Thread(target=gen_first, daemon=True)
        t.start()

    return RedirectResponse(url="/profile", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    session = get_session()
    state = session.query(JourneyState).first()
    logs = session.query(JourneyLog).order_by(JourneyLog.generated_at.desc()).all()

    location = None
    if state and state.current_location_id:
        location = session.query(Location).get(state.current_location_id)

    enriched = []
    for log in logs:
        loc_name = ""
        if log.location_id:
            loc = session.query(Location).get(log.location_id)
            loc_name = loc.name if loc else ""
        enriched.append({
            "id": log.id, "location_name": loc_name,
            "story_text": log.story_text, "image_path": log.image_path,
            "weather": log.weather, "mood": log.mood,
            "generated_at": log.generated_at,
        })

    session.close()
    return templates.TemplateResponse(request, "index.html", {
        "request": request, "state": state, "location": location, "logs": enriched,
    })


@app.post("/generate")
async def generate_now():
    """Manually trigger a new photo generation."""
    import threading
    def gen():
        Scheduler().run_generation()
    t = threading.Thread(target=gen, daemon=True)
    t.start()
    return {"status": "ok", "message": "Generation started"}
