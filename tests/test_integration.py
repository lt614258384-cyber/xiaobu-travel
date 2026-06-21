from fastapi.testclient import TestClient


def test_index_returns_200():
    from app import app
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "小布的旅行" in resp.text


def test_profile_page_returns_200():
    from app import app
    with TestClient(app) as client:
        resp = client.get("/profile")
    assert resp.status_code == 200
    assert "档案" in resp.text


def test_profile_save_works():
    from app import app
    with TestClient(app) as client:
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
