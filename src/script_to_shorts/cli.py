from __future__ import annotations

import argparse
from pathlib import Path

from script_to_shorts.pipeline import render


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="script-to-shorts",
        description="Turn a script into a vertical AI short (voice, visuals, captions).",
    )
    parser.add_argument("script", type=Path, help="Path to the script file")
    parser.add_argument("--out", type=Path, default=Path("output/short.mp4"), help="Output mp4 path")
    parser.add_argument("--voice", default=None, help="Edge TTS voice, e.g. en-IN-NeerjaNeural")
    parser.add_argument("--no-ai-images", action="store_true", help="Skip image generation; use text cards")
    args = parser.parse_args()

    if not args.script.exists():
        raise SystemExit(f"Script not found: {args.script}")

    render(
        script_path=args.script,
        out_path=args.out,
        voice=args.voice,
        use_ai_images=not args.no_ai_images,
    )


if __name__ == "__main__":
    main()
