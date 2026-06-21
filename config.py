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
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")

    def __post_init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.GENERATED_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
