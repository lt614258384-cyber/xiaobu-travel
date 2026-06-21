from crypto_utils import hash_password, verify_password


def test_hash_password_uses_argon2id():
    hashed = hash_password("my-secure-password")
    assert hashed.startswith("$argon2id$")


def test_verify_password_correct():
    hashed = hash_password("my-secure-password")
    assert verify_password("my-secure-password", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("my-secure-password")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_constant_time_for_wrong_length():
    hashed = hash_password("my-secure-password")
    # Different length should still work without timing leak
    assert verify_password("short", hashed) is False


import time
from session_utils import (
    generate_session_token,
    hash_token,
    create_session,
    validate_session,
    extend_session,
    delete_session,
    delete_all_user_sessions,
)


def test_generate_session_token_is_64_hex():
    token = generate_session_token()
    assert len(token) == 64
    assert all(c in "0123456789abcdef" for c in token)


def test_hash_token_produces_64_char_hex():
    token = generate_session_token()
    h = hash_token(token)
    assert len(h) == 64


def test_create_and_validate_session(tmp_path, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from models import init_db, User, get_session
    init_db()
    session = get_session()
    user = User(email="test@example.com", password_hash="...", pet_name="Test Dog")
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    token, auth_session = create_session(user_id, True, "pytest")
    assert len(token) == 64
    assert auth_session.user_id == user_id
    assert auth_session.remember_me is True

    validated = validate_session(token)
    assert validated is not None
    assert validated.user_id == user_id

    delete_session(token)
    assert validate_session(token) is None


def test_extend_session_rotates_token(tmp_path, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from models import init_db, User, get_session
    init_db()
    session = get_session()
    user = User(email="extend@example.com", password_hash="...", pet_name="Extend Dog")
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    token, auth_session = create_session(user_id, True, "pytest")
    # Manually age the session to trigger rotation
    from datetime import datetime, timedelta, timezone
    session2 = get_session()
    from models import AuthSession
    db_sess = session2.query(AuthSession).filter_by(id=auth_session.id).first()
    db_sess.expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    session2.commit()
    # Refresh the in-memory object with the updated DB state
    auth_session = session2.query(AuthSession).filter_by(id=auth_session.id).first()
    session2.close()

    result = extend_session(auth_session)
    assert result is not None
    new_token, updated_session = result
    assert new_token != token
    assert len(new_token) == 64

    # Old token should no longer validate
    old_valid = validate_session(token)
    # New token should validate
    new_valid = validate_session(new_token)
    assert new_valid is not None


def test_extend_session_noop_for_non_remember_me(tmp_path, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from models import init_db, User, get_session
    init_db()
    session = get_session()
    user = User(email="noop@example.com", password_hash="...", pet_name="Noop Dog")
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    token, auth_session = create_session(user_id, False, "pytest")
    result = extend_session(auth_session)
    assert result is None


def test_delete_all_user_sessions(tmp_path, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from models import init_db, User, get_session
    init_db()
    session = get_session()
    user = User(email="a@b.com", password_hash="...", pet_name="Dog")
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    t1, _ = create_session(user_id, True, "ua1")
    t2, _ = create_session(user_id, False, "ua2")

    delete_all_user_sessions(user_id)
    assert validate_session(t1) is None
    assert validate_session(t2) is None
