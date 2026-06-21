import os
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["IMAGE_API_TYPE"] = "fake"

from fastapi.testclient import TestClient
from app import app
from models import init_db

# Ensure tables exist before tests run
init_db()


def test_index_returns_200():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "小布的旅行" in resp.text


def test_profile_page_returns_200():
    client = TestClient(app)
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "档案" in resp.text


def test_profile_save_works():
    client = TestClient(app)
    resp = client.post("/profile", data={
        "name": "小布",
        "breed": "柯基",
        "age": 3,
        "appearance": "一只奶油色柯基，大耳朵",
        "personality_tags": '["活泼","贪吃"]',
        "interests": '["追球","晒太阳"]',
        "habits": "每天早上要散步",
        "content_preference": "caption",
    })
    assert resp.status_code in [200, 303]
