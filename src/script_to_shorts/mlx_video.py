from __future__ import annotations

import math
import os
import platform
import re
import subprocess
from collections import deque
from pathlib import Path
from typing import Callable

import imageio_ffmpeg

from script_to_shorts.config import SETTINGS

WAN_FPS = 16
FASTMETAL_MODEL = "fastmetal-1.3B-QAD"
FASTMETAL_5B_MODEL = "fastmetal-5B-QAD"
FASTMETAL_14B_MODEL = "fastmetal-14B-QAD"


def generate_scene_video(
    prompt: str,
    duration: float,
    dest: Path,
    model: str | None = None,
    quantize: int | None = None,
    on_progress: Callable[[int, str], None] | None = None,
) -> Path:
    """Generate one animated scene with FastMetal or the MLX Wan 2.1 runner."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("MLX video generation requires Apple Silicon macOS.")

    model_name = model or SETTINGS.mlx_model
    if model_name == FASTMETAL_MODEL:
        return _generate_fastmetal_video(prompt, duration, dest, on_progress, model_name)
    if model_name == FASTMETAL_5B_MODEL:
        return _generate_fastmetal_5b_video(prompt, duration, dest, on_progress)
    if model_name == FASTMETAL_14B_MODEL:
        return _generate_fastmetal_video(prompt, duration, dest, on_progress, model_name)

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
    python_command = _resolve_python(SETTINGS.mlx_python)
    command = [
        python_command,
        str(runner),
        prompt,
        "--model",
        model_name,
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
    _run_command(command, wan_dir, dest, on_progress, "Loading MLX Wan model")
    return dest


def _generate_fastmetal_video(
    prompt: str,
    duration: float,
    dest: Path,
    on_progress: Callable[[int, str], None] | None,
    model_name: str,
) -> Path:
    """Run FastVideo's 3-step FastMetal-QAD Apple Silicon inference path."""
    fastvideo_dir = SETTINGS.fastvideo_dir.expanduser().resolve()
    runner = fastvideo_dir / "examples/inference/basic/mlx_wan_prompt_to_video.py"
    if not runner.is_file():
        raise FileNotFoundError(
            "FastVideo runner not found. Clone hao-ai-lab/FastVideo and install its MLX extra. "
            f"Expected: {runner}"
        )
    python_command = _resolve_python(SETTINGS.fastvideo_python)
    if len(Path(python_command).parts) > 1 and not Path(python_command).is_file():
        raise FileNotFoundError(
            "FastVideo Python environment not found. Create FastVideo/.venv and install "
            f"FastVideo's MLX extra. Expected: {python_command}"
        )

    width, height = map(int, SETTINGS.mlx_size.lower().split("x", maxsplit=1))
    frames = max(17, math.ceil((duration * WAN_FPS - 1) / 4) * 4 + 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        python_command,
        str(runner),
        "--prompt",
        prompt,
        "--height",
        str(height),
        "--width",
        str(width),
        "--num-frames",
        str(frames),
        "--fps",
        str(WAN_FPS),
        "--fast",
        "--fast-factor",
        "2",
        "--output-path",
        str(dest.resolve()),
    ]
    model_dir = (
        SETTINGS.fastmetal_14b_model_dir.strip()
        if model_name == FASTMETAL_14B_MODEL
        else SETTINGS.fastmetal_model_dir.strip()
    )
    if model_dir:
        model_path = Path(model_dir).expanduser()
        if not model_path.is_absolute():
            model_path = (Path.cwd() / model_path).resolve()
    elif model_name == FASTMETAL_14B_MODEL:
        model_path = _download_model_root("FastVideo/FastMetal-14B-QAD")
    else:
        model_path = None
    if model_path is not None:
        command.extend(["--model-root", str(model_path), "--mlx-checkpoint", str(model_path)])
    model_label = "FastMetal 14B" if model_name == FASTMETAL_14B_MODEL else "FastMetal 1.3B"
    _run_command(
        command,
        fastvideo_dir,
        dest,
        on_progress,
        f"Loading {model_label} · first run may download its checkpoint",
    )
    return dest


def _generate_fastmetal_5b_video(
    prompt: str,
    duration: float,
    dest: Path,
    on_progress: Callable[[int, str], None] | None,
) -> Path:
    """Run the higher-detail Wan 2.2 5B FastMetal MLX checkpoint."""
    fastvideo_dir = SETTINGS.fastvideo_dir.expanduser().resolve()
    runner = fastvideo_dir / "examples/inference/basic/mlx_wan22_generate.py"
    if not runner.is_file():
        raise FileNotFoundError(f"FastVideo Wan 2.2 runner not found: {runner}")
    python_command = _resolve_python(SETTINGS.fastvideo_python)
    if len(Path(python_command).parts) > 1 and not Path(python_command).is_file():
        raise FileNotFoundError(f"FastVideo Python environment not found: {python_command}")

    model_dir = SETTINGS.fastmetal_5b_model_dir.strip()
    model_path = Path(model_dir).expanduser() if model_dir else _download_model_root("FastVideo/FastMetal-5B-QAD")
    if not model_path.is_absolute():
        model_path = (Path.cwd() / model_path).resolve()
    # Use FastVideo's validated 480p shape. A 720p decode can request a single
    # Metal buffer larger than the 14.3 GiB limit on this Mac.
    frames = max(17, math.ceil((duration * 24 - 1) / 4) * 4 + 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        python_command,
        str(runner),
        "--prompt", prompt,
        "--height", "448",
        "--width", "832",
        "--num-frames", str(frames),
        "--fps", "24",
        "--text-encoder-root", str(model_path),
        "--mlx-checkpoint", str(model_path),
        "--vae-root", str(model_path / "vae"),
        "--output-path", str(dest.resolve()),
    ]
    _run_command(command, fastvideo_dir, dest, on_progress, "Loading FastMetal 5B · first run downloads its checkpoint")
    return dest


def _download_model_root(repo_id: str) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(
        repo_id=repo_id,
        allow_patterns=[
            "scheduler/*", "tokenizer/*", "text_encoder/*", "vae/*",
            "mlx_dit.json", "mlx_dit.safetensors", "ema/mlx_dit.json", "ema/mlx_dit.safetensors",
        ],
    ))


def _resolve_python(value: str) -> str:
    python = Path(value).expanduser()
    if not python.is_absolute() and len(python.parts) > 1:
        # Preserve venv ``bin/python`` symlinks. Resolving the final component
        # follows it to the system interpreter and drops the venv site-packages.
        return str(Path(os.path.abspath(Path.cwd() / python)))
    return str(python)


def _run_command(
    command: list[str],
    cwd: Path,
    dest: Path,
    on_progress: Callable[[int, str], None] | None,
    starting_message: str,
) -> None:
    if on_progress:
        on_progress(0, starting_message)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    ffmpeg_dir = str(Path(imageio_ffmpeg.get_ffmpeg_exe()).parent)
    env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
    try:
        output_tail: deque[str] = deque(maxlen=8)
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            output_tail.append(line.rstrip())
            match = re.search(r"(\d+)%.*?(\d+)/(\d+)", line)
            if match and on_progress:
                percent = int(match.group(1))
                on_progress(percent, f"Generating frames · {match.group(2)}/{match.group(3)} steps")
        return_code = process.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, command)
    except subprocess.CalledProcessError as exc:
        details = "\n".join(output_tail).strip()
        suffix = f"\nRuntime details:\n{details}" if details else ""
        raise RuntimeError(
            f"MLX video generation failed (exit code {exc.returncode}). "
            "Check the selected runtime, model setup, and available memory."
            f"{suffix}"
        ) from exc
    if not dest.is_file():
        raise RuntimeError(
            "The video model finished but did not save the output. "
            "Check the runtime logs for a decoding or FFmpeg error."
        )
