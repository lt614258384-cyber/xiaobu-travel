import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

@dataclass
class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///xiaobu.db")
    IMAGE_API_KEY: str = os.getenv("IMAGE_API_KEY", "")
    IMAGE_API_TYPE: str = os.getenv("IMAGE_API_TYPE", "tongyi")
    UPLOAD_DIR: Path = field(default_factory=lambda: Path("data/uploads"))
    GENERATED_DIR: Path = field(default_factory=lambda: Path("data/generated"))
    MAX_REFERENCE_PHOTOS: int = 10
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB per-file limit
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")

    def __post_init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    def check_production_safety(self):
        """If ENV=production, perform startup safety checks. Raises RuntimeError."""
        is_prod = os.getenv("ENV", "").lower() == "production"
        issues = []

        if self.SECRET_KEY == "dev-secret-change-me" or len(self.SECRET_KEY) < 32:
            msg = "SECRET_KEY must be 32+ chars high-entropy value"
            if is_prod:
                issues.append(msg)
            else:
                import warnings
                warnings.warn(msg)

        if issues:
            raise RuntimeError(f"Production safety check failed: {'; '.join(issues)}")

settings = Settings()
