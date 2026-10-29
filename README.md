# script-to-shorts

Local browser app and CLI for generating video and speech audio from prompts or scripts.

## Pipeline

1. Parse scenes from the script
2. Generate narration (Edge TTS online, or Piper offline)
3. Generate a still per scene (Pollinations online, SDXL-Turbo offline, or a text card), or animated clips with MLX Wan 2.1 on Apple Silicon
4. Add burned-in captions and narration, then assemble the scenes
5. Concatenate into `output/short.mp4`

Image-based modes create stills with a slow zoom. MLX Wan mode generates a moving video clip for every scene.

## Setup

Needs Python 3.10+ and (on macOS) Xcode Command Line Tools so `python3` / `pip` work. If `python3` is 3.9, use Homebrew `python3.12`.

```bash
cd ~/Projects/script-to-shorts
python3.12 -m venv .venv
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

## Local HTML app

Launch the browser app from the project folder:

```bash
./run_local_app.command
```

It opens `http://127.0.0.1:8765` and provides two modes:

- **Text to video:** describe a shot and generate a clip with MLX Wan 2.1. The first run downloads model weights.
- **Text to audio:** enter words to speak, then generate a WAV with local Piper or an MP3 with online Edge TTS.

Results are saved under `output/web/`. Keep the terminal window open while the app is running; press Ctrl+C there to stop it.

## Run fully local

Needs extra packages (PyTorch, diffusers, Piper). On Apple Silicon this uses MPS.

```bash
source .venv/bin/activate
pip install -e ".[local]"
python -m script_to_shorts --download-models
python -m script_to_shorts examples/sample_script.txt --local --out output/ep01_local.mp4
```

That downloads:

- Piper voice `en_US-lessac-medium` (~60MB)
- `stabilityai/sdxl-turbo` (~6–7GB, Hugging Face cache)

After the first download, renders do not need the network.

## Generate animated video locally with MLX Wan 2.1

This option requires an Apple Silicon Mac. The default 1.3B text-to-video model is the best starting point; Wan 2.1's 14B model has much higher memory requirements. The first generation downloads model weights from Hugging Face.

Clone Apple's MLX examples beside this project, then install the Wan runner's dependencies into this project's virtual environment:

```bash
cd ~/Projects
git clone https://github.com/ml-explore/mlx-examples.git
cd ~/Projects/script-to-shorts
source .venv/bin/activate
pip install -r ../mlx-examples/video/wan2.1/requirements.txt
```

Render an animated short:

```bash
script-to-shorts path/to/your-script.txt --mlx-video --out output/animated.mp4
```

For the 14B model, request 8-bit quantization to reduce memory use. It can still exceed available memory on some Macs:

```bash
script-to-shorts path/to/your-script.txt --mlx-video --mlx-model t2v-14B --mlx-quantize 8 --out output/animated-14b.mp4
```

The default settings expect the MLX examples checkout at `../mlx-examples/video/wan2.1` and use this project's active Python environment. Copy `.env.example` to `.env` before changing settings:

```env
MLX_WAN_DIR=../mlx-examples/video/wan2.1
MLX_PYTHON=.venv/bin/python
MLX_MODEL=t2v-1.3B
MLX_SIZE=480x832
MLX_STEPS=30
```

Hugging Face authentication is read from `hf auth login` or the `HF_TOKEN` environment variable. Prefer `hf auth login`; if you set `HF_TOKEN`, put the real value only in your local `.env` file. `.env` is ignored by Git, so never commit the token or paste it into chat.

Wan renders without audio; this project adds its narration and captions and crops the generated portrait clips to the configured 9:16 output size. Use detailed visual descriptions in each `VISUAL:` field. Text-to-video generates each scene independently, so repeat the character's appearance in each scene prompt when you want continuity.

## Next upgrades

- Swap Pollinations stills for Kling / Runway / Veo clips per scene
- Whisper word-level captions
- Background music bed
- LLM that breaks a raw idea into SCENE blocks
