from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts


async def _synthesize(text: str, voice: str, dest: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(dest))


def speak(text: str, voice: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize(text, voice, dest))
    return dest
