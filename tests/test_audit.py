from audit import log_event
from models import AuditLog, get_session


def test_log_event_writes_to_audit_log(tmp_path, monkeypatch):
    from config import settings
    db_path = tmp_path / "audit_test.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    from models import init_db
    init_db()

    log_event("user.login_success", user_id=42, ip_address="127.0.0.1",
              user_agent="pytest", details={"method": "email"})

    sess = get_session()
    try:
        entry = sess.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert entry.event == "user.login_success"
        assert entry.user_id == 42
        assert entry.ip_address == "127.0.0.1"
        assert entry.details == {"method": "email"}
    finally:
        sess.close()


def test_log_event_handles_none_user_id(tmp_path, monkeypatch):
    from config import settings
    db_path = tmp_path / "audit_test2.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    from models import init_db
    init_db()

    log_event("user.login_failed", user_id=None, ip_address="10.0.0.1",
              user_agent="pytest")

    sess = get_session()
    try:
        entry = sess.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert entry.user_id is None
    finally:
        sess.close()
