from __future__ import annotations

import json
import mimetypes
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from script_to_shorts.config import SETTINGS
from script_to_shorts.mlx_video import generate_scene_video
from script_to_shorts.tts import audio_suffix, speak

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = Path("output/web").resolve()
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="media-generation")
MAX_REQUEST_BYTES = 32_000
MAX_PROMPT_CHARS = 8_000


def _run_job(job_id: str, request: dict) -> None:
    with JOBS_LOCK:
        JOBS[job_id].update(status="running", progress=0, message="Starting generation")
    try:
        mode = request["mode"]
        prompt = request["prompt"].strip()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if mode == "video":
            seconds = max(2, min(int(request.get("seconds", 5)), 20))
            model = request.get("model", "fastmetal-1.3B-QAD")
            if model == "fastmetal-5B-QAD" and seconds > 5:
                raise ValueError("FastMetal 5B is limited to 5 seconds at 480p on this Mac to avoid Metal memory errors. Choose FastMetal 1.3B for longer clips.")
            quantize = request.get("quantize")
            if quantize not in (None, 4, 8):
                quantize = None
            output = OUTPUT_DIR / f"{job_id}.mp4"
            generate_scene_video(
                prompt,
                float(seconds),
                output,
                model=model,
                quantize=quantize,
                on_progress=lambda percent, message: _set_progress(job_id, percent, message),
            )
            kind = "video"
        elif mode == "audio":
            provider = request.get("provider", "local")
            if provider not in ("local", "edge"):
                provider = "local"
            voice = request.get("voice", SETTINGS.local_voice if provider == "local" else SETTINGS.voice)
            output = OUTPUT_DIR / f"{job_id}{audio_suffix(provider)}"
            with JOBS_LOCK:
                JOBS[job_id].update(progress=None, message="Creating speech audio")
            speak(prompt, voice, output, provider=provider)
            kind = "audio"
        else:
            raise ValueError("Choose video or audio generation.")

        with JOBS_LOCK:
            JOBS[job_id].update(
                status="done",
                url=f"/files/{job_id}",
                kind=kind,
                filename=output.name,
            )
    except Exception as exc:
        print(f"Generation job {job_id} failed: {exc}", flush=True)
        with JOBS_LOCK:
            JOBS[job_id].update(status="error", error=str(exc))


def _set_progress(job_id: str, progress: int, message: str) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(progress=progress, message=message)


class AppHandler(BaseHTTPRequestHandler):
    server_version = "ScriptToShortsLocal/1.0"

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if route.startswith("/api/status/"):
            job_id = route.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                response = dict(job) if job else None
            if response is None:
                self._send_json({"error": "Generation job not found."}, status=404)
            else:
                self._send_json(response)
            return
        if route == "/api/settings/hf-token":
            from huggingface_hub import get_token

            self._send_json({"configured": bool(get_token())})
            return
        if route.startswith("/files/"):
            self._serve_generated_file(route.rsplit("/", 1)[-1])
            return
        self.send_error(404)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/settings/hf-token":
            self._save_hf_token()
            return
        if route != "/api/generate":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("Request is empty or too large.")
            payload = json.loads(self.rfile.read(length))
            mode = payload.get("mode")
            prompt = payload.get("prompt", "")
            if mode not in ("video", "audio"):
                raise ValueError("Choose a generation mode.")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Enter a prompt first.")
            if len(prompt) > MAX_PROMPT_CHARS:
                raise ValueError(f"Prompt must be {MAX_PROMPT_CHARS} characters or fewer.")
            if mode == "video" and payload.get("model", "fastmetal-1.3B-QAD") not in (
                "fastmetal-1.3B-QAD",
                "fastmetal-5B-QAD",
                "fastmetal-14B-QAD",
                "t2v-1.3B",
                "t2v-14B",
            ):
                raise ValueError("Unsupported video model.")
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        job_id = uuid.uuid4().hex
        with JOBS_LOCK:
            JOBS[job_id] = {"status": "queued"}
        EXECUTOR.submit(_run_job, job_id, payload)
        self._send_json({"id": job_id, "status": "queued"}, status=202)

    def _save_hf_token(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000:
                raise ValueError("Enter a valid Hugging Face token.")
            payload = json.loads(self.rfile.read(length))
            token = payload.get("token", "")
            if not isinstance(token, str) or not token.startswith("hf_") or len(token) > 512:
                raise ValueError("Enter a valid Hugging Face access token beginning with hf_.")
            from huggingface_hub import login

            login(token=token, add_to_git_credential=False)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        except Exception:
            # Never return or log the submitted credential or a library error
            # that could include request details.
            self._send_json({"error": "Hugging Face rejected the token or could not save it locally."}, status=400)
            return
        self._send_json({"saved": True})

    def _serve_generated_file(self, job_id: str) -> None:
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            filename = job.get("filename") if job and job.get("status") == "done" else None
        if not filename:
            self.send_error(404)
            return
        path = (OUTPUT_DIR / filename).resolve()
        if path.parent != OUTPUT_DIR or not path.is_file():
            self.send_error(404)
            return
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self._send_file(path, mime_type)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                self.wfile.write(chunk)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Script to Shorts is running at http://{host}:{port}")
    print(f"Generated files will be saved to: {OUTPUT_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local app...")
    finally:
        server.shutdown()
        server.server_close()
        EXECUTOR.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
