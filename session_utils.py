import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from models import get_session, AuthSession, CsrfToken


def generate_session_token() -> str:
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_session(user_id: int, remember_me: bool, user_agent: str) -> "tuple[str, AuthSession]":
    token = generate_session_token()
    token_hash_val = hash_token(token)
    expires_at = _utcnow() + timedelta(days=7) if remember_me else _utcnow() + timedelta(hours=24)
    sess = get_session()
    try:
        auth_session = AuthSession(
            user_id=user_id,
            token_hash=token_hash_val,
            expires_at=expires_at,
            remember_me=remember_me,
            user_agent=user_agent,
        )
        sess.add(auth_session)
        sess.commit()
        sess.refresh(auth_session)
        return token, auth_session
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


_MAX_SESSION_AGE = timedelta(days=30)  # absolute expiry regardless of remember_me


def validate_session(token: str) -> "AuthSession | None":
    token_hash_val = hash_token(token)
    sess = get_session()
    try:
        auth_session = sess.query(AuthSession).filter_by(token_hash=token_hash_val).first()
        if auth_session is None:
            return None
        # Check absolute expiry (30 days from creation)
        if auth_session.created_at:
            created = auth_session.created_at.replace(tzinfo=timezone.utc) if auth_session.created_at.tzinfo is None else auth_session.created_at
            if created + _MAX_SESSION_AGE < _utcnow():
                sess.query(CsrfToken).filter_by(session_id=auth_session.id).delete()
                sess.delete(auth_session)
                sess.commit()
                return None
        # Check session expiry
        if auth_session.expires_at.replace(tzinfo=timezone.utc) < _utcnow():
            try:
                sess.query(CsrfToken).filter_by(session_id=auth_session.id).delete()
                sess.delete(auth_session)
                sess.commit()
            except Exception:
                sess.rollback()
                raise
            return None
        return auth_session
    finally:
        sess.close()


def extend_session(auth_session: "AuthSession") -> "tuple[str, AuthSession] | None":
    if not auth_session.remember_me:
        return None
    now = _utcnow()
    if auth_session.expires_at.replace(tzinfo=timezone.utc) - now > timedelta(hours=24):
        return None
    sess = get_session()
    try:
        new_token = generate_session_token()
        sess.query(AuthSession).filter_by(id=auth_session.id).update(
            {"token_hash": hash_token(new_token), "expires_at": now + timedelta(days=7)}
        )
        sess.commit()
        auth_session.token_hash = hash_token(new_token)
        auth_session.expires_at = now + timedelta(days=7)
        return new_token, auth_session
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


def delete_session(token: str) -> None:
    token_hash_val = hash_token(token)
    sess = get_session()
    try:
        auth_sess = sess.query(AuthSession).filter_by(token_hash=token_hash_val).first()
        if auth_sess:
            sess.query(CsrfToken).filter_by(session_id=auth_sess.id).delete()
            sess.delete(auth_sess)
            sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


def delete_all_user_sessions(user_id: int) -> None:
    sess = get_session()
    try:
        auth_sessions = sess.query(AuthSession).filter_by(user_id=user_id).all()
        for auth_sess in auth_sessions:
            sess.query(CsrfToken).filter_by(session_id=auth_sess.id).delete()
            sess.delete(auth_sess)
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()
