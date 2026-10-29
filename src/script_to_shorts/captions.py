from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from script_to_shorts.config import SETTINGS


def caption_chunks(text: str, duration: float) -> list[tuple[float, float, str]]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    groups: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= 4 or word.endswith((".", "?", "!")):
            groups.append(" ".join(current))
            current = []
    if current:
        groups.append(" ".join(current))

    total_chars = sum(len(g) for g in groups) or 1
    t = 0.0
    timed: list[tuple[float, float, str]] = []
    for group in groups:
        span = duration * (len(group) / total_chars)
        timed.append((t, min(duration, t + span), group))
        t += span
    if timed:
        start, _, text_last = timed[-1]
        timed[-1] = (start, duration, text_last)
    return timed


def render_caption_png(text: str, dest: Path) -> Path:
    width, height = SETTINGS.width, SETTINGS.height
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _font(72)
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = _wrap(text.upper(), font, dummy, width - 120)
    line_h = 90
    block_h = line_h * len(lines)
    y = height - 420 - block_h
    for line in lines:
        w = dummy.textlength(line, font=font)
        x = (width - w) / 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))
        y += line_h
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest)
    return dest


def _font(size: int):
    for name in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "Arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font, dummy: ImageDraw.ImageDraw, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if dummy.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]
