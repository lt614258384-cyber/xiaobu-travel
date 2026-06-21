from pathlib import Path
from unittest.mock import patch

import app as app_module
from config import settings
from models import Profile, get_session


def test_profile_upload_with_chinese_names_uses_ascii_filename(
    tmp_path, monkeypatch, authenticated_client
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    settings.UPLOAD_DIR.mkdir()

    client, user_id, csrf_token = authenticated_client

    with (
        patch.object(app_module.Scheduler, "start"),
        patch.object(app_module.Scheduler, "shutdown"),
        patch.object(app_module.Scheduler, "run_generation"),
    ):
        response = client.post(
            "/profile",
            data={
                "name": "小布",
                "_csrf_token": csrf_token,
            },
            files={"photos": ("小布正面照.PNG", b"image-bytes", "image/png")},
        )

    assert response.status_code == 303
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
    assert (settings.UPLOAD_DIR / str(user_id) / filename).read_bytes() == b"image-bytes"
