from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    voice: str = os.getenv("VOICE", "en-US-JennyNeural")
    width: int = int(os.getenv("WIDTH", "1080"))
    height: int = int(os.getenv("HEIGHT", "1920"))
    fps: int = int(os.getenv("FPS", "30"))
    image_provider: str = os.getenv("IMAGE_PROVIDER", "pollinations")
    work_dir: Path = Path(os.getenv("WORK_DIR", "output/work"))


SETTINGS = Settings()
