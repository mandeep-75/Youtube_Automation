# YouTube Automation Pipeline

> Turn any raw video into a narrated, subtitled, AI-voiced YouTube Short — then upload it automatically every day.

## Tech Stack

- **Vision**: Ollama + Qwen3.5:0.8b for frame analysis
- **LLM**: Ollama + Qwen3.5:9b for script generation
- **TTS**: MLX Qwen3-TTS (Apple Silicon) for AI voice narration
- **Transcription**: Faster-Whisper (base model)
- **Video Processing**: OpenCV, Pillow, imageio-ffmpeg, FFmpeg
- **Upload**: google-api-python-client (YouTube), instagrapi (Instagram)

## 8-Step Pipeline

```
Step 1 → Extract frames at 2-second intervals
Step 2 → Describe each frame with Qwen VL
Step 3 → Transcribe original audio with Whisper
Step 4 → Generate narration script with LLM
Step 5 → Generate TTS audio
Step 6 → Merge video + audio
Step 7 → Transcribe for subtitles
Step 8 → Burn subtitles into video
```

## Features

- **Auto-processing**: Watcher detects new videos and runs the full pipeline
- **Auto-upload**: Runs on boot + every 24 hours (one video per day)
- **YouTube + Instagram**: Upload to both platforms
- **Original audio option**: Mix original audio with TTS
- **Hallucination detection**: Validates frame descriptions against images

## Quick Start

```bash
# Pull Ollama models
ollama pull qwen3.5:0.8b
ollama pull qwen3.5:9b

# Setup Python environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Authenticate YouTube
.venv/bin/python -m src.uploaders.interactive_uploader
```

## Commands

```bash
# Run watcher (auto-processes new videos)
.venv/bin/python -m src.watcher

# Process a video manually
.venv/bin/python pipeline.py /path/to/video.mp4

# Auto-upload
bash scripts/auto_service.sh

# Lint
.venv/bin/ruff check .

# Type check
.venv/bin/mypy .
```

## Requirements

- Python 3.14
- FFmpeg (`brew install ffmpeg`)
- Ollama running locally with `qwen3.5:0.8b` and `qwen3.5:9b` models
