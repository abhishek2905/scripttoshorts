from __future__ import annotations

import math
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Callable

import imageio_ffmpeg

from script_to_shorts.config import SETTINGS

WAN_FPS = 16


def generate_scene_video(
    prompt: str,
    duration: float,
    dest: Path,
    model: str | None = None,
    quantize: int | None = None,
    on_progress: Callable[[int, str], None] | None = None,
) -> Path:
    """Generate one animated scene with the MLX Wan 2.1 example runner."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("MLX Wan video generation requires Apple Silicon macOS.")

    wan_dir = SETTINGS.mlx_wan_dir.expanduser().resolve()
    runner = wan_dir / "txt2video.py"
    if not runner.is_file():
        raise FileNotFoundError(
            "MLX Wan runner not found. Clone mlx-examples and set MLX_WAN_DIR to "
            f"its video/wan2.1 folder. Expected: {runner}"
        )

    # Wan requires 4n+1 frames. Round up so the generated clip covers narration.
    frames = max(17, math.ceil((duration * WAN_FPS - 1) / 4) * 4 + 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    python = Path(SETTINGS.mlx_python).expanduser()
    if not python.is_absolute() and len(python.parts) > 1:
        python_command = str((Path.cwd() / python).resolve())
    else:
        python_command = str(python)
    command = [
        python_command,
        str(runner),
        prompt,
        "--model",
        model or SETTINGS.mlx_model,
        "--size",
        SETTINGS.mlx_size,
        "--frames",
        str(frames),
        "--steps",
        str(SETTINGS.mlx_steps),
        "--no-cache",
        "--output",
        str(dest.resolve()),
    ]
    if quantize is not None:
        command.extend(["--quantize", str(quantize)])
    if on_progress:
        on_progress(0, "Loading model and preparing prompt")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    ffmpeg_dir = str(Path(imageio_ffmpeg.get_ffmpeg_exe()).parent)
    env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
    try:
        process = subprocess.Popen(
            command,
            cwd=wan_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            match = re.search(r"(\d+)%.*?(\d+)/(\d+)", line)
            if match and on_progress:
                percent = int(match.group(1))
                on_progress(percent, f"Generating frames · {match.group(2)}/{match.group(3)} steps")
        return_code = process.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, command)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"MLX Wan failed for scene video (exit code {exc.returncode}). "
            "Check the MLX Wan environment and available memory."
        ) from exc
    if not dest.is_file():
        raise RuntimeError(
            "Wan finished generating frames but did not save the video. "
            "The MLX video runner needs FFmpeg on PATH."
        )
    return dest
