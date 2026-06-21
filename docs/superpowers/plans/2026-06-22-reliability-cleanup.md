# Reliability Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace deprecated startup hooks, make uploaded reference-photo paths encoding-safe, and remove legacy Ghibli style terms from seed and persisted activity prompts.

**Architecture:** A FastAPI lifespan owns one `Scheduler` instance and performs idempotent prompt cleanup before serving requests. Upload naming and prompt sanitization are isolated in small pure helpers, while database cleanup and scheduler shutdown wrap those helpers with explicit resource management.

**Tech Stack:** Python 3.13, FastAPI 0.115, SQLAlchemy 2.0, APScheduler 3.10, pytest 8.3

---

## File map

- Create `seed/prompt_cleanup.py`: pure prompt sanitization plus persisted-activity cleanup.
- Create `tests/test_prompt_cleanup.py`: sanitizer, database cleanup, and all-seed regression coverage.
- Modify `seed/activities_data.py`: remove legacy style suffixes from the 203 source templates.
- Modify `engine/storyteller.py`: remove the runtime legacy-string workaround.
- Modify `scheduler.py`: expose safe scheduler shutdown.
- Modify `tests/test_scheduler.py`: verify running and stopped shutdown behavior.
- Modify `app.py`: define lifespan and use safe upload filenames.
- Create `tests/test_lifespan.py`: verify startup/shutdown resource ownership.
- Create `uploads.py`: generate ASCII reference-photo filenames and web paths.
- Create `tests/test_uploads.py`: verify Chinese names upload to safe ASCII paths.
- Modify `docs/CONTEXT.md`: mark the three known issues as resolved.

### Task 1: Remove legacy Prompt style data

**Files:**
- Create: `tests/test_prompt_cleanup.py`
- Create: `seed/prompt_cleanup.py`
- Modify: `seed/activities_data.py`
- Modify: `engine/storyteller.py`

- [ ] **Step 1: Write failing tests for sanitization, persistence, and all seed templates**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Activity, Base, Location, Region
from seed.activities_data import generate_activities
from seed.prompt_cleanup import (
    cleanup_activity_prompt_templates,
    sanitize_prompt_template,
)


def test_sanitize_prompt_template_removes_legacy_style_terms_idempotently():
    original = "{appearance} 在海边散步，吉卜力动画风格，温暖治愈"
    cleaned = sanitize_prompt_template(original)

    assert cleaned == "{appearance} 在海边散步"
    assert sanitize_prompt_template(cleaned) == cleaned


def test_cleanup_activity_prompt_templates_updates_existing_rows():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        region = Region(name="测试区")
        session.add(region)
        session.flush()
        location = Location(region_id=region.id, name="测试地")
        session.add(location)
        session.flush()
        session.add(Activity(
            location_id=location.id,
            name="散步",
            prompt_template="海边散步，吉卜力动画风格",
        ))
        session.commit()

    changed = cleanup_activity_prompt_templates(lambda: Session(engine))

    with Session(engine) as session:
        activity = session.query(Activity).one()
        assert activity.prompt_template == "海边散步"
    assert changed == 1
    assert cleanup_activity_prompt_templates(lambda: Session(engine)) == 0


def test_all_seed_prompt_templates_exclude_legacy_style_terms():
    activities = generate_activities()
    templates = [
        activity["prompt_template"]
        for location_activities in activities.values()
        for activity in location_activities
    ]

    assert len(templates) == 203
    assert all("吉卜力动画风格" not in template for template in templates)
    assert all("温暖治愈" not in template for template in templates)
```

- [ ] **Step 2: Run the tests and confirm the intended RED state**

Run: `python -m pytest tests/test_prompt_cleanup.py -v`

Expected: collection fails because `seed.prompt_cleanup` does not exist. Create only an empty module, rerun, and confirm assertions fail because the sanitizer and cleanup functions are absent or do not remove the terms.

To turn the expected import error into a behavioral failure before implementation, add this temporary skeleton and rerun:

```python
def sanitize_prompt_template(template: str) -> str:
    return template


def cleanup_activity_prompt_templates(session_factory=None) -> int:
    return 0
```

Expected after the skeleton: assertions fail because the old terms remain and persisted rows are unchanged. Replace the skeleton in Step 3.

- [ ] **Step 3: Implement the minimal prompt cleanup module**

```python
import re
from collections.abc import Callable

from sqlalchemy.orm import Session

from models import Activity, get_session

LEGACY_STYLE_TERMS = ("吉卜力动画风格", "温暖治愈")


def sanitize_prompt_template(template: str) -> str:
    cleaned = template
    for term in LEGACY_STYLE_TERMS:
        cleaned = cleaned.replace(term, "")
    cleaned = re.sub(r"，{2,}", "，", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ，")


def cleanup_activity_prompt_templates(
    session_factory: Callable[[], Session] | None = None,
) -> int:
    session = (session_factory or get_session)()
    changed = 0
    try:
        for activity in session.query(Activity).all():
            cleaned = sanitize_prompt_template(activity.prompt_template or "")
            if cleaned == activity.prompt_template:
                continue
            activity.prompt_template = cleaned
            changed += 1
        session.commit()
        return changed
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 4: Remove legacy terms from the source seed data**

Mechanically replace `，吉卜力动画风格，温暖治愈` and `，吉卜力动画风格` with an empty string in `seed/activities_data.py`. Then run:

`rg -n "吉卜力|温暖治愈" seed/activities_data.py`

Expected: no matches.

- [ ] **Step 5: Remove the Storyteller runtime workaround**

Delete these lines from `engine/storyteller.py`:

```python
        # Strip Ghibli/anime keywords
        base = base.replace("吉卜力动画风格", "").replace("温暖治愈", "").replace("，吉卜力动画风格", "")
```

- [ ] **Step 6: Run focused tests and confirm GREEN**

Run: `python -m pytest tests/test_prompt_cleanup.py tests/test_storyteller.py -v`

Expected: all tests pass.

- [ ] **Step 7: Commit prompt cleanup**

```bash
git add seed/prompt_cleanup.py seed/activities_data.py engine/storyteller.py tests/test_prompt_cleanup.py
git commit -m "fix: remove legacy prompt style terms"
```

### Task 2: Add safe Scheduler shutdown

**Files:**
- Modify: `tests/test_scheduler.py`
- Modify: `scheduler.py`

- [ ] **Step 1: Write failing shutdown tests**

```python
    def test_shutdown_stops_running_scheduler_without_waiting(self):
        scheduler = Scheduler()
        scheduler._aps = MagicMock()
        scheduler._aps.running = True

        scheduler.shutdown()

        scheduler._aps.shutdown.assert_called_once_with(wait=False)

    def test_shutdown_is_safe_when_scheduler_is_not_running(self):
        scheduler = Scheduler()
        scheduler._aps = MagicMock()
        scheduler._aps.running = False

        scheduler.shutdown()

        scheduler._aps.shutdown.assert_not_called()
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_scheduler.py -v`

Expected: both new tests fail with `AttributeError: 'Scheduler' object has no attribute 'shutdown'`.

- [ ] **Step 3: Add the minimal shutdown method**

```python
    def shutdown(self) -> None:
        if not self._aps.running:
            return
        self._aps.shutdown(wait=False)
```

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_scheduler.py -v`

Expected: all scheduler tests pass.

- [ ] **Step 5: Commit scheduler shutdown**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "fix: stop scheduler during app shutdown"
```

### Task 3: Replace deprecated FastAPI startup hook with lifespan

**Files:**
- Create: `tests/test_lifespan.py`
- Modify: `app.py`

- [ ] **Step 1: Write a failing lifespan ownership test**

```python
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as app_module


def test_lifespan_initializes_resources_and_stops_scheduler():
    with (
        patch.object(app_module, "init_db") as init_db,
        patch.object(app_module, "cleanup_activity_prompt_templates", create=True) as cleanup,
        patch.object(app_module, "Scheduler") as scheduler_class,
    ):
        scheduler = scheduler_class.return_value

        with TestClient(app_module.app):
            assert getattr(app_module.app.state, "scheduler", None) is scheduler

        init_db.assert_called_once_with()
        cleanup.assert_called_once_with()
        scheduler.start.assert_called_once_with()
        scheduler.shutdown.assert_called_once_with()
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_lifespan.py -v`

Expected: fails because the startup hook does not save the Scheduler on `app.state`, does not clean prompt data, and has no shutdown path.

- [ ] **Step 3: Implement lifespan in `app.py`**

```python
from contextlib import asynccontextmanager

from seed.prompt_cleanup import cleanup_activity_prompt_templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cleanup_activity_prompt_templates()
    scheduler = Scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown()
        app.state.scheduler = None


app = FastAPI(title="小布的旅行", lifespan=lifespan)
```

Remove the old `@app.on_event("startup")` function.

- [ ] **Step 4: Run lifespan and integration tests**

Run: `python -m pytest tests/test_lifespan.py tests/test_integration.py -v`

Expected: all tests pass without a FastAPI `on_event` deprecation warning.

- [ ] **Step 5: Commit lifespan migration**

```bash
git add app.py tests/test_lifespan.py
git commit -m "refactor: manage app resources with lifespan"
```

### Task 4: Generate encoding-safe uploaded photo paths

**Files:**
- Create: `uploads.py`
- Create: `tests/test_uploads.py`
- Modify: `app.py`

- [ ] **Step 1: Write a failing route-level upload test**

```python
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as app_module
from config import settings
from models import Profile, get_session


def test_profile_upload_with_chinese_names_uses_ascii_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'uploads.db'}")
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    settings.UPLOAD_DIR.mkdir()

    with (
        patch.object(app_module.Scheduler, "start"),
        patch.object(app_module.Scheduler, "shutdown"),
        patch.object(app_module.Scheduler, "run_generation"),
        TestClient(app_module.app) as client,
    ):
        response = client.post(
            "/profile",
            data={"name": "小布"},
            files={"photos": ("小布正面照.PNG", b"image-bytes", "image/png")},
        )

    assert response.status_code == 200
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
    assert (settings.UPLOAD_DIR / filename).read_bytes() == b"image-bytes"
```

- [ ] **Step 2: Run the route test and verify RED**

Run: `python -m pytest tests/test_uploads.py -v`

Expected: fails because the current saved filename contains the Chinese profile name and keeps the uppercase extension.

- [ ] **Step 3: Implement focused upload naming helpers**

```python
from pathlib import Path
from uuid import uuid4

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def make_reference_photo_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        suffix = ".jpg"
    return f"ref_{uuid4().hex}{suffix}"


def make_reference_photo_web_path(filename: str) -> str:
    return (Path("data/uploads") / filename).as_posix()
```

- [ ] **Step 4: Use the helpers in the profile route**

Import both functions in `app.py`, then replace the filename/path construction with:

```python
            filename = make_reference_photo_filename(photo.filename)
            filepath = settings.UPLOAD_DIR / filename
            with open(filepath, "wb") as file_handle:
                shutil.copyfileobj(photo.file, file_handle)
            photo_paths.append(make_reference_photo_web_path(filename))
```

- [ ] **Step 5: Run upload and integration tests**

Run: `python -m pytest tests/test_uploads.py tests/test_integration.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit safe upload naming**

```bash
git add uploads.py app.py tests/test_uploads.py
git commit -m "fix: use safe reference photo filenames"
```

### Task 5: Update context and verify the complete maintenance batch

**Files:**
- Modify: `docs/CONTEXT.md`

- [ ] **Step 1: Update the known-issues section**

Move the completed FastAPI startup, Chinese upload filename, and seed Prompt cleanup items into a short “已完成的可靠性改进” subsection. Keep the unresolved character consistency, PostgreSQL deployment, notifications, and Seedream 5.0 items under “未来方向”.

- [ ] **Step 2: Verify source invariants**

Run: `rg -n "on_event" app.py`

Expected: no matches.

Run: `rg -n "吉卜力动画风格|温暖治愈" seed/activities_data.py engine/storyteller.py`

Expected: no matches. The sanitizer constants and test fixtures intentionally retain the terms so the cleanup behavior can be exercised.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -v`

Expected: all tests pass with zero failures.

- [ ] **Step 4: Inspect the final diff**

Run: `git status --short && git diff --check && git diff --stat HEAD~4..HEAD`

Expected: no whitespace errors; only the planned source, test, and context files are tracked changes. Existing untracked runtime files remain untouched.

- [ ] **Step 5: Commit documentation**

```bash
git add docs/CONTEXT.md
git commit -m "docs: record reliability improvements"
```
