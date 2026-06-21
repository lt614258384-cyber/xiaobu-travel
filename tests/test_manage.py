import subprocess
import sys
from pathlib import Path


def test_init_owner_creates_admin_and_migrates(tmp_path, monkeypatch):
    from config import settings
    db_path = tmp_path / "manage_test.db"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    from models import init_db
    init_db()

    # Create some orphan data
    from models import get_session, Profile, JourneyState
    sess = get_session()
    p = Profile(name="Old Profile")
    sess.add(p)
    js = JourneyState(mood="happy", day_number=1)
    sess.add(js)
    sess.commit()
    sess.close()

    result = subprocess.run(
        [sys.executable, "manage.py", "init-owner", "--email", "admin@test.com",
         "--password", "securepass123", "--pet-name", "小布"],
        cwd=Path(__file__).parent.parent,
        capture_output=True, text=True,
        env={**__import__("os").environ, "DATABASE_URL": f"sqlite:///{db_path}"}
    )
    assert "创建管理员" in result.stdout
    assert "2 条旧记录" in result.stdout or "迁移了" in result.stdout
