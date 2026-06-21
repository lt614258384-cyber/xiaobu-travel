"""Tests for cross-user data isolation."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def two_users(authenticated_client):
    """Set up two users: user A (authenticated) and user B."""
    from models import get_session, User, Profile
    from crypto_utils import hash_password

    client_a, user_id_a, csrf_token = authenticated_client

    sess = get_session()
    # Create user B
    user_b = User(
        email="other@example.com",
        password_hash=hash_password("pass12345"),
        pet_name="OtherDog",
        is_admin=False,
    )
    sess.add(user_b)
    sess.commit()
    user_id_b = user_b.id

    # Create profiles for both users with distinct data
    profile_a = Profile(
        user_id=user_id_a,
        name="UserADog",
        breed="柯基",
        age=3,
        appearance="奶油色柯基",
    )
    profile_b = Profile(
        user_id=user_id_b,
        name="UserBDog",
        breed="金毛",
        age=5,
        appearance="金色长毛",
    )
    sess.add(profile_a)
    sess.add(profile_b)
    sess.commit()
    sess.close()

    return client_a, user_id_a, user_id_b, csrf_token


def test_user_cannot_see_other_users_profile(two_users):
    """User A's profile page should not contain user B's data."""
    client_a, user_id_a, user_id_b, csrf_token = two_users

    resp = client_a.get("/profile")
    assert resp.status_code == 200

    # User A should see their own profile data
    assert "UserADog" in resp.text
    assert "柯基" in resp.text

    # User A should NOT see user B's profile data
    assert "UserBDog" not in resp.text
    assert "金毛" not in resp.text
    assert "金色长毛" not in resp.text


def test_user_cannot_update_other_users_profile(two_users):
    """POST to /profile as user A should update only user A's profile."""
    client_a, user_id_a, user_id_b, csrf_token = two_users

    # Update user A's profile
    resp = client_a.post("/profile", data={
        "name": "UpdatedDogA",
        "breed": "哈士奇",
        "age": 4,
        "_csrf_token": csrf_token,
    }, follow_redirects=False)
    assert resp.status_code == 303

    # Verify user A's profile was updated
    from models import get_session, Profile
    sess = get_session()
    profile_a = sess.query(Profile).filter_by(user_id=user_id_a).first()
    profile_b = sess.query(Profile).filter_by(user_id=user_id_b).first()
    assert profile_a is not None
    assert profile_a.name == "UpdatedDogA"
    # User B's profile should remain unchanged
    assert profile_b is not None
    assert profile_b.name == "UserBDog"
    sess.close()


def test_two_users_have_separate_index_pages(two_users):
    """User A's index page should show only their own journey data."""
    client_a, user_id_a, user_id_b, csrf_token = two_users

    # Add a journey log for user B
    from models import get_session, JourneyLog, Location, Activity, Region
    sess = get_session()
    region = Region(name="测试区域", description="测试")
    sess.add(region)
    sess.commit()
    location = Location(region_id=region.id, name="测试地点", description="测试")
    sess.add(location)
    sess.commit()
    activity = Activity(location_id=location.id, name="测试活动")
    sess.add(activity)
    sess.commit()
    log_b = JourneyLog(
        user_id=user_id_b,
        location_id=location.id,
        activity_id=activity.id,
        story_text="User B's secret story",
        image_path="data/generated/test.png",
        weather="晴",
        mood="开心",
    )
    sess.add(log_b)
    sess.commit()
    sess.close()

    # User A visits index page
    resp = client_a.get("/")
    assert resp.status_code == 200
    # User A should NOT see user B's story
    assert "User B" not in resp.text
    assert "secret story" not in resp.text


def test_user_cannot_access_index_without_auth():
    """Unauthenticated access to / should redirect to /login."""
    from app import app
    with TestClient(app) as client:
        resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
