from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Scene:
    index: int
    visual: str
    narration: str


@dataclass
class Script:
    title: str
    scenes: list[Scene]


SCENE_RE = re.compile(r"^SCENE\s+(\d+)\s*$", re.IGNORECASE)
FIELD_RE = re.compile(r"^(VISUAL|NARRATION|VOICEOVER|VO)\s*:\s*(.*)$", re.IGNORECASE)


def parse_script(path: Path) -> Script:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Script is empty: {path}")

    if re.search(r"^SCENE\s+\d+", text, re.IGNORECASE | re.MULTILINE):
        return _parse_marked(text)
    return _parse_plain(text)


def _parse_marked(text: str) -> Script:
    title = "Untitled short"
    scenes: list[Scene] = []
    current: dict[str, str] | None = None
    current_index = 0
    buffer_key: str | None = None

    def flush() -> None:
        nonlocal current, current_index
        if not current:
            return
        narration = current.get("narration", "").strip()
        visual = current.get("visual", "").strip()
        if not narration:
            raise ValueError(f"SCENE {current_index} is missing NARRATION")
        if not visual:
            visual = narration
        scenes.append(Scene(index=current_index, visual=visual, narration=narration))
        current = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            buffer_key = None
            continue
        if line.upper().startswith("TITLE:"):
            title = line.split(":", 1)[1].strip() or title
            buffer_key = None
            continue
        scene_match = SCENE_RE.match(line.strip())
        if scene_match:
            flush()
            current_index = int(scene_match.group(1))
            current = {}
            buffer_key = None
            continue
        field = FIELD_RE.match(line.strip())
        if field:
            key = field.group(1).lower()
            key = "narration" if key in {"voiceover", "vo", "narration"} else "visual"
            if current is None:
                current_index = len(scenes) + 1
                current = {}
            current[key] = field.group(2).strip()
            buffer_key = key
            continue
        if current is not None and buffer_key:
            current[buffer_key] = (current[buffer_key] + " " + line.strip()).strip()

    flush()
    if not scenes:
        raise ValueError("No scenes found in script")
    return Script(title=title, scenes=scenes)


def _parse_plain(text: str) -> Script:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = "Untitled short"
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0].split(":", 1)[1].strip() or title
        lines = lines[1:]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", "\n".join(lines)) if p.strip()]
    if not paragraphs:
        paragraphs = lines
    scenes = [
        Scene(index=i, visual=paragraph, narration=paragraph)
        for i, paragraph in enumerate(paragraphs, start=1)
    ]
    return Script(title=title, scenes=scenes)
