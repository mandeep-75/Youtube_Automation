# YouTube Automation Pipeline

Turn raw video into narrated, subtitled YouTube Shorts.

## Requirements

- Python 3.14+
- [FFmpeg](https://ffmpeg.org) (`brew install ffmpeg`)
- [Ollama](https://ollama.ai) running locally with models: `qwen3.5:0.8b`, `qwen3.5:9b`

## Quick Start

```bash
# Setup
make setup              # create venv + install deps
make models             # pull Ollama models
make check              # verify everything is ready

# Process a video
make run VIDEO=video.mp4

# Debug mode (2 frames only, faster)
make dev VIDEO=video.mp4
```

## Pipeline

1. **Extract & describe frames** — extract frames at 2s intervals, describe with Qwen VL
2. **Transcribe & generate script** — transcribe original audio, write narration script
3. **Generate TTS audio** — Kitten TTS (ONNX-based, CPU-optimized)
4. **Render final video** — merge A/V, transcribe for subtitles, burn them in

Output: `yt_inbox/outputs/<video_name>/final_video.mp4`

## Configuration

All settings in `src/config.py`:
- `FRAME_INTERVAL` — frame extraction rate (default: 2.0s)
- `VISION_MODEL` / `LLM_MODEL` — Ollama models
- `WHISPER_MODEL` — transcription model size
- `SUBTITLE_FONTS` — font selection for burn-in
- `DEBUG_MODE` — set `True` for faster testing (2 frames)

## Project Structure

```
├── pipeline.py             # Main entry point
├── Makefile                # Convenience commands
├── src/
│   ├── config.py           # All settings
│   ├── steps/              # 8 pipeline step scripts
│   └── utils/              # FFmpeg helpers, logger
├── yt_inbox/outputs/       # Processed output per video
├── fonts/                  # Subtitle font files (TTF)
├── samples/                # TTS reference audio (me.mp3)
└── tools/                  # FFmpeg + setup checker
```
