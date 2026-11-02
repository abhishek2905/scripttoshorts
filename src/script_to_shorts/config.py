from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    voice: str = os.getenv("VOICE", "en-US-JennyNeural")
    local_voice: str = os.getenv("LOCAL_VOICE", "en_US-lessac-medium")
    width: int = int(os.getenv("WIDTH", "1080"))
    height: int = int(os.getenv("HEIGHT", "1920"))
    fps: int = int(os.getenv("FPS", "30"))
    tts_provider: str = os.getenv("TTS_PROVIDER", "edge")
    image_provider: str = os.getenv("IMAGE_PROVIDER", "pollinations")
    image_model: str = os.getenv("IMAGE_MODEL", "stabilityai/sdxl-turbo")
    models_dir: Path = Path(os.getenv("MODELS_DIR", "models"))
    work_dir: Path = Path(os.getenv("WORK_DIR", "output/work"))
    mlx_wan_dir: Path = Path(os.getenv("MLX_WAN_DIR", "../mlx-examples/video/wan2.1"))
    mlx_python: str = os.getenv("MLX_PYTHON", sys.executable)
    mlx_model: str = os.getenv("MLX_MODEL", "fastmetal-1.3B-QAD")
    mlx_size: str = os.getenv("MLX_SIZE", "480x832")
    mlx_steps: int = int(os.getenv("MLX_STEPS", "30"))
    fastvideo_dir: Path = Path(os.getenv("FASTVIDEO_DIR", "../FastVideo"))
    fastvideo_python: str = os.getenv("FASTVIDEO_PYTHON", "../FastVideo/.venv/bin/python")
    fastmetal_model_dir: str = os.getenv("FASTMETAL_MODEL_DIR", "")
    fastmetal_5b_model_dir: str = os.getenv("FASTMETAL_5B_MODEL_DIR", "")
    fastmetal_14b_model_dir: str = os.getenv("FASTMETAL_14B_MODEL_DIR", "")


SETTINGS = Settings()
