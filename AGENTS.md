# AGENTS.md — YouTube Automation Pipeline

## Commands

```bash
make setup              # .venv + pip install -r requirements.txt
make models             # pull ollama models: qwen3.5:0.8b, qwen3.5:9b
make check              # verify env with tools/check_setup.py
make lint               # .venv/bin/ruff check .
make typecheck          # .venv/bin/mypy .
make run VIDEO=x.mp4    # full pipeline
make dev VIDEO=x.mp4    # debug mode (2 frames)
make run VIDEO=x.mp4 SCRIPT_REF="--script-ref ref.txt"  # with reference script for tone
.venv/bin/python pipeline.py --debug --script-ref ref.txt video.mp4
.venv/bin/python src/steps/step1_analyze.py --video-file x.mp4 --interval 2.0 --output-dir frames --frames-file frames.txt
.venv-qwen3-tts/bin/python -c "from qwen_tts import Qwen3TTSModel"
tail -f logs/pipeline_*.log
```

## Qwen3-TTS (voice clone)

```bash
make tts-all              # create .venv-qwen3-tts + download models
make tts-setup            # venv + pip install qwen-tts
make tts-models           # download tokenizer + 1.7B-Base to models/qwen3-tts/
```

| Model | Path |
|-------|------|
| Tokenizer | `models/qwen3-tts/Qwen3-TTS-Tokenizer-12Hz/` |
| Voice Clone (1.7B) | `models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-Base/` |

Python: `.venv-qwen3-tts/bin/python` (Python 3.14) or `.venv/bin/python` (Python 3.11, used by pipeline). flash-attn not available on macOS (no CUDA).

No pytest. No tests at all.

## Architecture

- `pipeline.py` is the entrypoint — calls 4 step scripts as subprocesses via `config.PIPELINE_PYTHON` (`.venv/bin/python`)
- Each step script is standalone (can run independently) and does `sys.path.insert` to reach project root
- `src/config.py` is mutable — `pipeline.py` sets `config.DEBUG_MODE = True` at runtime before steps execute
- `src/utils/` is empty — no helpers there despite README claiming otherwise
- Config values set at module import, read by steps at runtime

## Step outputs

| Step | Produces |
|------|----------|
| 1 analyze | `yt_inbox/<name>/frames/` (PNGs), `frames.txt` (timestamped descriptions) |
| 2 script | `yt_inbox/<name>/transcript.txt`, `script.txt`, `script.thinking.txt` |
| 3 tts | `yt_inbox/<name>/voice.wav` |
| 4 render | `yt_inbox/<name>/<name>.mp4` (final video) |

All files for a video live inside `yt_inbox/<video_name>/`. Intermediates and final video are in the same folder.

## Quirks & gotchas

- **FFmpeg resolution order:** `tools/ffmpeg` → `imageio_ffmpeg` → system `$PATH`. Same for ffprobe.
- **Ollama must be running** at `http://localhost:11434`. Pipeline will fail silently-ish without it.
- **Whisper model downloads** on first `faster-whisper` use (auto, ~150MB for `base`).
- **`--script-ref`** feeds a reference script into the LLM prompt to influence tone/style. Pass any text file path.
- **Python 3.11+** (Makefile uses `python3.11 -m venv`; README says 3.14+).
- **No `pathlib`** — codebase uses `os.path` exclusively.
- **`FRAME_INTERVAL`** is a string `"2.0"` in config (passed as CLI arg), not a float.

## Key config knobs (`src/config.py`)

| Setting | Default | Notes |
|---------|---------|-------|
| `DEBUG_MODE` | `False` | Set `True` → `DEBUG_MAX_FRAMES=2` frames extracted |
| `FRAME_INTERVAL` | `"2.0"` | String, passed to argparse |
| `VISION_MODEL` | `qwen3.5:0.8b` | Ollama vision model |
| `LLM_MODEL` | `qwen3.5:9b` | Ollama text model for script gen |
| `LLM_WORDS_PER_SECOND` | `4` | Target pacing for generated script |
| `WHISPER_MODEL` | `base` | faster-whisper model size |
| `TTS_SPEED` | `1.2` | |
| `TTS_REF_AUDIO` | `"voice_ref.wav"` | Reference audio for voice clone |
| `TTS_REF_TEXT` | `""` | Transcript of reference audio |
| `SUBTITLE_MAX_WORDS` | `3` | Words per subtitle chunk |
| `SUBTITLE_POSITION` | `"center"` | Also `"top"` / `"bottom"` |
