from __future__ import annotations

import asyncio
import wave
from pathlib import Path

import edge_tts

from script_to_shorts.config import SETTINGS

_piper_voice = None


def audio_suffix(provider: str) -> str:
    return ".wav" if provider == "local" else ".mp3"


def speak(text: str, voice: str, dest: Path, provider: str = "edge") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if provider == "local":
        return _speak_piper(text, voice, dest)
    asyncio.run(_synthesize_edge(text, voice, dest))
    return dest


async def _synthesize_edge(text: str, voice: str, dest: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(dest))


def _speak_piper(text: str, voice: str, dest: Path) -> Path:
    from script_to_shorts.local_models import PIPER_VOICES, piper_paths

    global _piper_voice
    local_voice = voice if voice in PIPER_VOICES else SETTINGS.local_voice
    if _piper_voice is None or getattr(_piper_voice, "_sts_name", None) != local_voice:
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise SystemExit(
                "Local TTS needs piper-tts. Install with: pip install -e '.[local]'"
            ) from exc
        model, config = piper_paths(local_voice)
        loaded = PiperVoice.load(str(model), config_path=str(config))
        loaded._sts_name = local_voice
        _piper_voice = loaded
        print(f"  loaded Piper voice {local_voice}")

    wav_path = dest.with_suffix(".wav")
    with wave.open(str(wav_path), "wb") as wav_file:
        _piper_voice.synthesize_wav(text, wav_file)
    return wav_path
