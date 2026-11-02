# script-to-shorts

Local browser app and CLI for generating video and speech audio from prompts or scripts.

## Pipeline

1. Parse scenes from the script
2. Generate narration (Edge TTS online, or Piper offline)
3. Generate a still per scene (Pollinations online, SDXL-Turbo offline, or a text card), or animated clips with FastMetal/MLX Wan on Apple Silicon
4. Add burned-in captions and narration, then assemble the scenes
5. Concatenate into `output/short.mp4`

Image-based modes create stills with a slow zoom. The browser app uses FastMetal-QAD for fast prompt-to-video; the script workflow can also render scenes with MLX Wan.

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

- **Text to video:** select FastMetal 1.3B for speed or FastMetal 5B for higher detail, with Wan 2.1 still available. FastMetal 14B is listed for Macs with 36GB+ unified memory. The first run downloads model weights.
- **Text to audio:** choose local Hindi male/female Piper voices, or online Edge TTS voices including Hindi and several Indian English tones.
- **Hugging Face token:** paste it into the optional video setting to save it in your local Hugging Face credentials. This can help with authenticated downloads, but does not make generation itself faster. The app never writes it into the project.

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

## Set up fast local video with FastMetal-QAD

FastMetal-QAD is a 3-step, pre-quantized Wan-based model made for Apple Silicon. The project uses FastVideo's MLX runtime. Its first generation downloads the checkpoint from Hugging Face; `hf auth login` is supported.

Clone FastVideo beside this project and install its MLX environment:

```bash
brew install uv ffmpeg
cd ~/Projects
git clone https://github.com/hao-ai-lab/FastVideo.git
cd FastVideo
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install -e "[mlx]"
cd ~/Projects/script-to-shorts
```

The default settings expect the checkout and its environment at `../FastVideo` and `../FastVideo/.venv/bin/python`. Copy `.env.example` to `.env` before overriding these paths.

The app's Text to video tab selects FastMetal by default. FastVideo downloads the FastMetal checkpoint on its first generation. You can also run it from the CLI:

```bash
script-to-shorts examples/patna_marine_drive.txt --mlx-video --mlx-model fastmetal-1.3B-QAD --out output/fastmetal.mp4
```

FastMetal is a 3-step checkpoint. Fast frame interpolation is enabled in the app. FastVideo reports about 58–110 seconds for a 5-second 480p clip on tested 24–36 GB Apple Silicon Macs; actual time depends on hardware, cache state, and prompt. FastMetal's MLX runner is separate from the original MLX examples checkout.

Choose `fastmetal-5B-QAD` for the higher-detail Wan 2.2 model. The app uses its validated 480p shape and limits clips to 5 seconds to avoid Metal buffer allocation errors. The model can generate at 720p in other setups, but that decode can exceed this Mac's buffer limit. `fastmetal-14B-QAD` is also available in the app, but needs a high-memory Mac; FastVideo recommends 36GB+ unified memory.

## Optional: use the original MLX Wan runner

Clone Apple's MLX examples beside this project and install its requirements into the project environment:

```bash
cd ~/Projects
git clone https://github.com/ml-explore/mlx-examples.git
cd ~/Projects/script-to-shorts
source .venv/bin/activate
pip install -r ../mlx-examples/video/wan2.1/requirements.txt
```

Run Wan 1.3B or 14B through the CLI:

```bash
script-to-shorts examples/patna_marine_drive.txt --mlx-video --mlx-model t2v-1.3B --out output/wan.mp4
```

The 14B model supports 8-bit quantization but can still exceed memory on 24 GB Macs:

```bash
script-to-shorts examples/patna_marine_drive.txt --mlx-video --mlx-model t2v-14B --mlx-quantize 8 --out output/wan-14b.mp4
```

Hugging Face authentication is read from `hf auth login` or the `HF_TOKEN` environment variable. Prefer `hf auth login`; if you set `HF_TOKEN`, put the real value only in your local `.env` file. `.env` is ignored by Git, so never commit the token or paste it into chat.

Text-to-video generates each scene independently, so repeat character details in prompts when you want continuity.

## Next upgrades

- Swap Pollinations stills for Kling / Runway / Veo clips per scene
- Whisper word-level captions
- Background music bed
- LLM that breaks a raw idea into SCENE blocks
