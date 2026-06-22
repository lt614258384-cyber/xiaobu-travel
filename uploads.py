from pathlib import Path
from uuid import uuid4
import io

from fastapi import HTTPException, status
from PIL import Image

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

# Magic-number signatures: first bytes -> canonical extension
_MAGIC_SIGNATURES = [
    (b'\xff\xd8\xff', '.jpg'),            # JPEG
    (b'\x89PNG\r\n\x1a\n', '.png'),       # PNG
]

# Extension -> Pillow format name mapping
_EXT_TO_PILLOW_FORMAT = {
    '.jpg': 'JPEG', '.jpeg': 'JPEG',
    '.png': 'PNG',
    '.webp': 'WEBP',
}


def _detect_webp(data: bytes) -> bool:
    """WebP: bytes 0-3 == b'RIFF', bytes 8-11 == b'WEBP'."""
    return len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP'


def validate_image_bytes(data: bytes, declared_suffix: str) -> None:
    """Validate uploaded image bytes for security and integrity.

    Checks performed in order:
      1. Size <= 10 MB
      2. Magic number matches a known image format
      3. Magic-implied extension matches the declared file extension
      4. Pillow Image.open().verify() succeeds (structural integrity)
      5. Pillow .format matches the declared extension

    Raises HTTPException with appropriate status code on failure.
    """
    # 1. Size
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"图片大小不能超过 {MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    # 2. Magic number
    detected_suffix = None
    for magic, ext in _MAGIC_SIGNATURES:
        if data.startswith(magic):
            detected_suffix = ext
            break
    if detected_suffix is None and _detect_webp(data):
        detected_suffix = '.webp'

    if detected_suffix is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="不支持的文件格式，仅支持 JPEG、PNG、WebP",
        )

    # 3. Extension vs. magic consistency
    declared = '.jpg' if declared_suffix == '.jpeg' else declared_suffix
    if detected_suffix != declared:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"文件扩展名与内容不匹配",
        )

    # 4. Pillow structural verify
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片数据损坏，无法读取",
        )

    # 5. Pillow format consistency (fresh BytesIO after verify())
    try:
        img2 = Image.open(io.BytesIO(data))
        pillow_format = img2.format
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片数据损坏，无法读取",
        )

    expected_format = _EXT_TO_PILLOW_FORMAT.get(declared)
    # Accept if format matches OR if magic number already confirmed it
    if expected_format and pillow_format and pillow_format != expected_format:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"文件格式不一致（检测到 {pillow_format}，期望 {expected_format}）",
        )


def make_reference_photo_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        suffix = ".jpg"
    return f"ref_{uuid4().hex}{suffix}"


def make_reference_photo_web_path(filename: str) -> str:
    return (Path("data/uploads") / filename).as_posix()
