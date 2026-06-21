import json
import shutil
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from models import get_session, Profile, init_db
from config import settings

app = FastAPI(title="小布的旅行")
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

    existing = profile.reference_photos or []
    photo_paths = list(existing)
    for photo in photos:
        if photo.filename and photo.size > 0:
            if len(photo_paths) >= settings.MAX_REFERENCE_PHOTOS:
                break
            ext = Path(photo.filename).suffix or ".jpg"
            filename = f"ref_{name}_{len(photo_paths)}{ext}"
            filepath = settings.UPLOAD_DIR / filename
            with open(filepath, "wb") as f:
                shutil.copyfileobj(photo.file, f)
            photo_paths.append(str(filepath.relative_to(Path.cwd())))

    profile.reference_photos = photo_paths[:settings.MAX_REFERENCE_PHOTOS]
    session.commit()
    session.close()
    return RedirectResponse(url="/profile", status_code=303)
