from __future__ import annotations

from pathlib import Path

from script_to_shorts.assemble import build_scene_clip, write_video
from script_to_shorts.config import SETTINGS
from script_to_shorts.parse import parse_script
from script_to_shorts.tts import speak
from script_to_shorts.visuals import scene_image


def render(script_path: Path, out_path: Path, voice: str | None = None, use_ai_images: bool = True) -> Path:
    script = parse_script(script_path)
    work = SETTINGS.work_dir / script_path.stem
    work.mkdir(parents=True, exist_ok=True)
    chosen_voice = voice or SETTINGS.voice
    clips = []

    print(f"Title: {script.title}")
    print(f"Scenes: {len(script.scenes)}")

    for scene in script.scenes:
        print(f"  [{scene.index}] TTS + image...")
        audio_path = work / f"scene_{scene.index:02d}.mp3"
        text_path = audio_path.with_suffix(".txt")
        image_path = work / f"scene_{scene.index:02d}.jpg"
        speak(scene.narration, chosen_voice, audio_path)
        text_path.write_text(scene.narration, encoding="utf-8")
        scene_image(scene.visual, image_path, use_ai=use_ai_images)
        clips.append(
            build_scene_clip(image_path, audio_path, work, scene.index, scene.narration)
        )

    result = write_video(clips, out_path)
    print(f"Wrote {result}")
    return result
