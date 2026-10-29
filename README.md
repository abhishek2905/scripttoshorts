# script-to-shorts

Local CLI: give it a script, get a vertical short (9:16) with voiceover, scene images, and captions.

## Pipeline

1. Parse scenes from the script
2. Generate narration with Edge TTS (free, no API key)
3. Generate a still per scene (Pollinations by default; falls back to a text card)
4. Ken Burns zoom + burned-in captions
5. Concatenate into `output/short.mp4`

This is the faceless-shorts pattern (still + voice + captions). Full motion video APIs (Kling, Runway, Veo) can plug into the same scene list later.

## Setup

Needs Python 3.10+ and (on macOS) Xcode Command Line Tools so `python3` / `pip` work.

```bash
cd ~/Projects/script-to-shorts
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

FFmpeg is pulled in via `imageio-ffmpeg`. You do not need a separate brew install.

## Script format

```
TITLE: Your episode title

SCENE 1
VISUAL: what the frame should look like
NARRATION: what the voice says

SCENE 2
VISUAL: ...
NARRATION: ...
```

Plain paragraphs also work: each paragraph becomes a scene, and the text is used for both voice and image prompt.

## Render

```bash
python -m script_to_shorts examples/sample_script.txt --out output/ep01.mp4
```

Indian English voice:

```bash
python -m script_to_shorts examples/sample_script.txt --voice en-IN-NeerjaNeural
```

Skip remote images:

```bash
python -m script_to_shorts examples/sample_script.txt --no-ai-images
```

## Next upgrades

- Swap Pollinations stills for Kling / Runway / Veo clips per scene
- Whisper word-level captions
- Background music bed
- LLM that breaks a raw idea into SCENE blocks
