from __future__ import annotations

from pathlib import Path

from moviepy import AudioFileClip

from script_to_shorts.assemble import build_animated_scene_clip, build_scene_clip, write_video
from script_to_shorts.config import SETTINGS
from script_to_shorts.mlx_video import generate_scene_video
from script_to_shorts.parse import parse_script
from script_to_shorts.tts import audio_suffix, speak
from script_to_shorts.visuals import scene_image


def render(
    script_path: Path,
    out_path: Path,
    voice: str | None = None,
    use_ai_images: bool = True,
    local: bool = False,
    mlx_video: bool = False,
    mlx_model: str | None = None,
    mlx_quantize: int | None = None,
) -> Path:
    script = parse_script(script_path)
    work = SETTINGS.work_dir / script_path.stem
    work.mkdir(parents=True, exist_ok=True)
    tts_provider = "local" if local else SETTINGS.tts_provider
    image_provider = "local" if local else SETTINGS.image_provider
    if not use_ai_images:
        image_provider = "none"
    if tts_provider == "local":
        chosen_voice = voice or SETTINGS.local_voice
    else:
        chosen_voice = voice or SETTINGS.voice
    clips = []

    print(f"Title: {script.title}")
    print(f"Scenes: {len(script.scenes)}")
    visual_mode = (
        f"MLX Wan ({mlx_model or SETTINGS.mlx_model})"
        if mlx_video
        else f"Images: {image_provider}"
    )
    print(f"TTS: {tts_provider}  {visual_mode}")

    for scene in script.scenes:
        print(f"  [{scene.index}] TTS + {'animated video' if mlx_video else 'image'}...")
        audio_path = work / f"scene_{scene.index:02d}{audio_suffix(tts_provider)}"
        text_path = audio_path.with_suffix(".txt")
        image_path = work / f"scene_{scene.index:02d}.jpg"
        audio_path = speak(scene.narration, chosen_voice, audio_path, provider=tts_provider)
        text_path.write_text(scene.narration, encoding="utf-8")
        if mlx_video:
            audio = AudioFileClip(str(audio_path))
            duration = audio.duration
            audio.close()
            video_path = work / f"scene_{scene.index:02d}.mp4"
            generate_scene_video(
                scene.visual,
                max(duration, 1.2),
                video_path,
                model=mlx_model,
                quantize=mlx_quantize,
            )
            clips.append(
                build_animated_scene_clip(
                    video_path, audio_path, work, scene.index, scene.narration
                )
            )
        else:
            scene_image(scene.visual, image_path, provider=image_provider)
            clips.append(
                build_scene_clip(image_path, audio_path, work, scene.index, scene.narration)
            )

    result = write_video(clips, out_path)
    print(f"Wrote {result}")
    return result
