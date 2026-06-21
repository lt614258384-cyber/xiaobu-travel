from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as app_module
from config import settings
from models import Profile, get_session


def test_profile_upload_with_chinese_names_uses_ascii_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'uploads.db'}")
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    settings.UPLOAD_DIR.mkdir()

    with (
        patch.object(app_module.Scheduler, "start"),
        patch.object(app_module.Scheduler, "shutdown"),
        patch.object(app_module.Scheduler, "run_generation"),
        TestClient(app_module.app) as client,
    ):
        response = client.post(
            "/profile",
            data={"name": "小布"},
            files={"photos": ("小布正面照.PNG", b"image-bytes", "image/png")},
        )

    assert response.status_code == 200
    session = get_session()
    try:
        profile = session.query(Profile).one()
        saved_path = profile.reference_photos[0]
    finally:
        session.close()

    filename = Path(saved_path).name
    assert filename.isascii()
    assert filename.startswith("ref_")
    assert filename.endswith(".png")
    assert (settings.UPLOAD_DIR / filename).read_bytes() == b"image-bytes"
