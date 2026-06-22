import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from PIL import Image

import app as app_module
from config import settings
from models import Profile, get_session
from uploads import validate_image_bytes, MAX_UPLOAD_SIZE


def _make_jpeg_bytes(w=10, h=10) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color="red").save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes(w=10, h=10) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (w, h), color=(0, 255, 0, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_webp_bytes(w=10, h=10) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color="blue").save(buf, format="WEBP")
    return buf.getvalue()


# ── Existing test updated with real image bytes ──

def test_profile_upload_with_chinese_names_uses_ascii_filename(
    tmp_path, monkeypatch, authenticated_client
):
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    settings.UPLOAD_DIR.mkdir()

    client, user_id, csrf_token = authenticated_client
    valid_png = _make_png_bytes()

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
            files={"photos": ("小布正面照.PNG", valid_png, "image/png")},
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
    assert (settings.UPLOAD_DIR / str(user_id) / filename).read_bytes() == valid_png


# ── New image validation unit tests ──

class TestValidateImageBytes:
    """Unit tests for validate_image_bytes()."""

    def test_accepts_valid_jpeg(self):
        validate_image_bytes(_make_jpeg_bytes(), ".jpg")

    def test_accepts_valid_jpeg_with_jpeg_extension(self):
        validate_image_bytes(_make_jpeg_bytes(), ".jpeg")

    def test_accepts_valid_png(self):
        validate_image_bytes(_make_png_bytes(), ".png")

    def test_accepts_valid_webp(self):
        validate_image_bytes(_make_webp_bytes(), ".webp")

    def test_rejects_non_image_bytes(self):
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(b"hello world, not an image!", ".jpg")
        assert exc.value.status_code == 415

    def test_rejects_empty_bytes(self):
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(b"", ".png")
        assert exc.value.status_code == 415

    def test_rejects_over_size_limit(self):
        oversized = b"\xff\xd8\xff" + b"\x00" * (MAX_UPLOAD_SIZE + 1)
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(oversized, ".jpg")
        assert exc.value.status_code == 413

    def test_accepts_reasonable_sized_valid_image(self):
        validate_image_bytes(_make_jpeg_bytes(800, 600), ".jpg")

    def test_rejects_jpeg_bytes_with_png_extension(self):
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(_make_jpeg_bytes(), ".png")
        assert exc.value.status_code == 415

    def test_rejects_png_bytes_with_webp_extension(self):
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(_make_png_bytes(), ".webp")
        assert exc.value.status_code == 415

    def test_rejects_corrupt_jpeg_header(self):
        corrupt = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(corrupt, ".jpg")
        assert exc.value.status_code == 400

    def test_rejects_truncated_png(self):
        png = _make_png_bytes()
        truncated = png[:len(png) // 2]
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(truncated, ".png")
        assert exc.value.status_code == 400

    def test_rejects_unknown_extension(self):
        with pytest.raises(HTTPException) as exc:
            validate_image_bytes(_make_jpeg_bytes(), ".gif")
        assert exc.value.status_code == 415
