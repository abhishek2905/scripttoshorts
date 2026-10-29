from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image, ImageDraw, ImageFont

from script_to_shorts.config import SETTINGS

_local_pipe = None


def scene_image(prompt: str, dest: Path, provider: str = "pollinations") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if provider == "local":
        try:
            _generate_local(prompt, dest)
            return dest
        except Exception as exc:
            print(f"  local image failed ({exc}); using text card")
            _fallback_card(prompt, dest)
            return dest
    if provider != "none":
        try:
            _download_pollinations(prompt, dest)
            return dest
        except Exception:
            pass
    _fallback_card(prompt, dest)
    return dest


def _torch_device():
    import torch

    if torch.backends.mps.is_available():
        return "mps", torch.float16
    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.float32


def _local_pipeline():
    global _local_pipe
    if _local_pipe is not None:
        return _local_pipe
    try:
        import torch
        from diffusers import AutoPipelineForText2Image
    except ImportError as exc:
        raise SystemExit(
            "Local images need torch + diffusers. Install with: pip install -e '.[local]'"
        ) from exc

    device, dtype = _torch_device()
    print(f"  loading {SETTINGS.image_model} on {device}...")
    pipe = AutoPipelineForText2Image.from_pretrained(
        SETTINGS.image_model,
        torch_dtype=dtype,
        variant="fp16" if dtype == torch.float16 else None,
    )
    pipe.to(device)
    _local_pipe = pipe
    return pipe


def _generate_local(prompt: str, dest: Path) -> None:
    pipe = _local_pipeline()
    full = (
        f"{prompt}, vertical 9:16, cinematic lighting, photoreal, "
        f"no text, no watermark, ultra detailed"
    )
    width = 768
    height = 1344
    image = pipe(
        prompt=full,
        num_inference_steps=4,
        guidance_scale=0.0,
        width=width,
        height=height,
    ).images[0]
    image = image.resize((SETTINGS.width, SETTINGS.height), Image.Resampling.LANCZOS)
    image.save(dest, format="JPEG", quality=92)


def _download_pollinations(prompt: str, dest: Path) -> None:
    full = (
        f"{prompt}, vertical 9:16, cinematic lighting, photoreal, "
        f"no text, no watermark, ultra detailed"
    )
    url = (
        "https://image.pollinations.ai/prompt/"
        f"{quote(full)}?width={SETTINGS.width}&height={SETTINGS.height}&nologo=true"
    )
    with httpx.Client(timeout=90.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
    image = image.resize((SETTINGS.width, SETTINGS.height), Image.Resampling.LANCZOS)
    image.save(dest, format="JPEG", quality=92)


def _fallback_card(prompt: str, dest: Path) -> None:
    width, height = SETTINGS.width, SETTINGS.height
    image = Image.new("RGB", (width, height), (12, 14, 22))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, int(height * 0.55), width, height), fill=(24, 32, 54))
    font = _font(54)
    wrapped = _wrap(prompt, font, width - 160)
    y = int(height * 0.62)
    for line in wrapped[:8]:
        draw.text((80, y), line, fill=(240, 240, 245), font=font)
        y += 70
    image.save(dest, format="JPEG", quality=92)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("Arial.ttf", "Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
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
    return lines
