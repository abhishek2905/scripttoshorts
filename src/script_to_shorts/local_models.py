from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

from script_to_shorts.config import SETTINGS

PIPER_REPO = "rhasspy/piper-voices"
PIPER_VOICES = {
    "en_US-lessac-medium": "en/en_US/lessac/medium/en_US-lessac-medium.onnx",
}


def piper_paths(voice: str | None = None) -> tuple[Path, Path]:
    name = voice or SETTINGS.local_voice
    rel = PIPER_VOICES.get(name)
    if rel is None:
        raise ValueError(
            f"Unknown local voice {name!r}. Available: {', '.join(PIPER_VOICES)}"
        )
    model = Path(hf_hub_download(repo_id=PIPER_REPO, filename=rel))
    config = Path(hf_hub_download(repo_id=PIPER_REPO, filename=f"{rel}.json"))
    return model, config


def download_image_model(model_id: str | None = None) -> Path:
    repo = model_id or SETTINGS.image_model
    return Path(snapshot_download(repo_id=repo))


def download_models(voice: str | None = None) -> None:
    print("Downloading Piper TTS voice...")
    model, config = piper_paths(voice)
    print(f"  voice: {model}")
    print(f"  config: {config}")
    print(f"Downloading image model {SETTINGS.image_model} (first time is several GB)...")
    cache = download_image_model()
    print(f"  cached at: {cache}")
    print("Models ready.")
