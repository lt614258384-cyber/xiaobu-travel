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
