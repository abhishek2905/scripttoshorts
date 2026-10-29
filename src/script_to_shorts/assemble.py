from __future__ import annotations

from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from script_to_shorts.captions import caption_chunks, render_caption_png
from script_to_shorts.config import SETTINGS


def build_scene_clip(
    image_path: Path,
    audio_path: Path,
    work_dir: Path,
    scene_index: int,
    narration: str,
):
    audio = AudioFileClip(str(audio_path))
    duration = max(audio.duration, 1.2)
    clip = (
        ImageClip(str(image_path))
        .with_duration(duration)
        .resized(lambda t: 1.0 + 0.08 * (t / duration))
        .with_position("center")
        .with_audio(audio)
    )
    overlays = []
    for i, (start, end, text) in enumerate(caption_chunks(narration, duration)):
        png = render_caption_png(text, work_dir / f"cap_{scene_index}_{i}.png")
        overlays.append(
            ImageClip(str(png))
            .with_start(start)
            .with_duration(max(end - start, 0.2))
        )
    return CompositeVideoClip([clip, *overlays], size=(SETTINGS.width, SETTINGS.height))


def build_animated_scene_clip(
    video_path: Path,
    audio_path: Path,
    work_dir: Path,
    scene_index: int,
    narration: str,
):
    audio = AudioFileClip(str(audio_path))
    duration = max(audio.duration, 1.2)
    source = VideoFileClip(str(video_path), audio=False)
    fitted = source.resized(height=SETTINGS.height)
    clip = (
        fitted.cropped(
            width=SETTINGS.width,
            height=SETTINGS.height,
            x_center=fitted.w / 2,
            y_center=fitted.h / 2,
        )
        .with_duration(duration)
        .with_audio(audio)
    )
    overlays = []
    for i, (start, end, text) in enumerate(caption_chunks(narration, duration)):
        png = render_caption_png(text, work_dir / f"cap_{scene_index}_{i}.png")
        overlays.append(
            ImageClip(str(png))
            .with_start(start)
            .with_duration(max(end - start, 0.2))
        )
    return CompositeVideoClip([clip, *overlays], size=(SETTINGS.width, SETTINGS.height))


def write_video(clips: list, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(
        str(dest),
        fps=SETTINGS.fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )
    final.close()
    for clip in clips:
        clip.close()
    return dest
