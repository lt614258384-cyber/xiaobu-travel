"""Tests for the authenticated GET /media/{path} route."""
import io

import pytest
from PIL import Image

import app as app_module
from models import get_session, JourneyLog, User
from crypto_utils import hash_password


def _create_test_file(base_dir, subdir, user_id, filename):
    """Create a real image file and return its bytes."""
    file_dir = base_dir / subdir / str(user_id)
    file_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    data = buf.getvalue()
    (file_dir / filename).write_bytes(data)
    return data


@pytest.fixture
def media_test_dir(tmp_path):
    """Set up isolated data directory with test files for two users."""
    data_dir = tmp_path / "data"
    _create_test_file(data_dir, "uploads", 1, "ref_test.jpg")
    _create_test_file(data_dir, "generated", 1, "gen_test.png")
    _create_test_file(data_dir, "uploads", 2, "ref_other.jpg")
    return data_dir


class TestMediaRoute:
    """Integration tests for GET /media/{path}."""

    def test_redirects_to_login_when_unauthenticated(self):
        from fastapi.testclient import TestClient
        from app import app
        with TestClient(app) as client:
            resp = client.get(
                "/media/uploads/1/ref_test.jpg", follow_redirects=False
            )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    def test_user_can_access_own_upload(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client
        resp = client.get(f"/media/uploads/{user_id}/ref_test.jpg")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/")

    def test_user_can_access_own_generated(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client
        resp = client.get(f"/media/generated/{user_id}/gen_test.png")
        assert resp.status_code == 200

    def test_user_cannot_access_other_users_file(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client
        resp = client.get("/media/uploads/2/ref_other.jpg")
        assert resp.status_code == 403

    def test_404_for_nonexistent_file(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client
        resp = client.get(f"/media/uploads/{user_id}/does_not_exist.jpg")
        assert resp.status_code == 404

    def test_path_traversal_blocked(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client
        resp = client.get(
            f"/media/uploads/{user_id}/../../../etc/passwd"
        )
        assert resp.status_code == 404

    def test_invalid_subdir_returns_404(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client
        resp = client.get(f"/media/features/{user_id}/something.txt")
        assert resp.status_code == 404

    def test_non_integer_user_id_returns_404(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client
        resp = client.get("/media/uploads/abc/file.jpg")
        assert resp.status_code == 404

    def test_api_latest_returns_media_path(
        self, authenticated_client, media_test_dir, monkeypatch
    ):
        """The /api/latest endpoint returns image_path with media/ prefix."""
        monkeypatch.setattr(app_module, "_DATA_ROOT", media_test_dir)
        client, user_id, csrf_token = authenticated_client

        # Create a journey log with a data/ path for this user
        sess = get_session()
        log = JourneyLog(
            user_id=user_id,
            location_id=1,
            activity_id=1,
            story_text="test",
            image_path="data/generated/1/test_img.png",
            weather="sunny",
            mood="happy",
        )
        sess.add(log)
        sess.commit()
        log_id = log.id
        sess.close()

        resp = client.get("/api/latest")
        data = resp.json()
        assert data["image_path"].startswith("media/")
        assert "data/" not in data["image_path"]

        # Cleanup
        sess = get_session()
        sess.query(JourneyLog).filter_by(id=log_id).delete()
        sess.commit()
        sess.close()
