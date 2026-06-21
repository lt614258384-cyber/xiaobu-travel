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
