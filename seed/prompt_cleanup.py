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
