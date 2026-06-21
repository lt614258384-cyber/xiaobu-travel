from __future__ import annotations
from datetime import datetime, timezone
from models import get_session, AuditLog


def log_event(
    event: str,
    user_id: int | None = None,
    ip_address: str = "",
    user_agent: str = "",
    details: dict | None = None,
) -> None:
    sess = get_session()
    try:
        entry = AuditLog(
            user_id=user_id,
            event=event,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
        sess.add(entry)
        sess.commit()
    except Exception:
        sess.rollback()
    finally:
        sess.close()
