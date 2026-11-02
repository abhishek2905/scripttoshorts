from __future__ import annotations

import argparse
from pathlib import Path

from script_to_shorts.config import SETTINGS
from script_to_shorts.pipeline import render


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="script-to-shorts",
        description="Turn a script into a vertical AI short (voice, visuals, captions).",
    )
    parser.add_argument("script", nargs="?", type=Path, help="Path to the script file")
    parser.add_argument("--out", type=Path, default=Path("output/short.mp4"), help="Output mp4 path")
    parser.add_argument(
        "--voice",
        default=None,
        help="Edge TTS voice (e.g. en-IN-NeerjaNeural) or local Piper voice (en_US-lessac-medium)",
    )
    parser.add_argument("--no-ai-images", action="store_true", help="Skip image generation; use text cards")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run fully offline: Piper TTS + SDXL-Turbo on this machine",
    )
    parser.add_argument(
        "--download-models",
        action="store_true",
        help="Download local TTS + image models, then exit unless a script is also given",
    )
    parser.add_argument(
        "--mlx-video",
        action="store_true",
        help="Generate animated scene clips with MLX Wan 2.1 (Apple Silicon Mac)",
    )
    parser.add_argument(
        "--mlx-model",
        choices=("fastmetal-1.3B-QAD", "fastmetal-5B-QAD", "fastmetal-14B-QAD", "t2v-1.3B", "t2v-14B"),
        default=SETTINGS.mlx_model,
        help="MLX text-to-video model (default: fastmetal-1.3B-QAD)",
    )
    parser.add_argument(
        "--mlx-quantize",
        type=int,
        choices=(4, 8),
        default=None,
        help="Quantize Wan's video transformer to 4 or 8 bit for lower memory use",
    )
    args = parser.parse_args()

    if args.download_models:
        from script_to_shorts.local_models import download_models

        download_models(args.voice)
        if args.script is None:
            return

    if args.script is None:
        parser.error("script is required unless you pass --download-models")

    if not args.script.exists():
        raise SystemExit(f"Script not found: {args.script}")

    render(
        script_path=args.script,
        out_path=args.out,
        voice=args.voice,
        use_ai_images=not args.no_ai_images,
        local=args.local,
        mlx_video=args.mlx_video,
        mlx_model=args.mlx_model if args.mlx_video else None,
        mlx_quantize=args.mlx_quantize,
    )


if __name__ == "__main__":
    main()
