# YouTube Automation Pipeline

> Turn any raw video into a narrated, subtitled, AI-voiced YouTube Short — then upload it automatically every day.

---

## Quick Start (first time only)

```bash
# 1. Pull the Ollama models
ollama pull qwen3.5:0.8b
ollama pull qwen3.5:9b

# 2. Create Python venv and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Authenticate YouTube (opens browser once)
.venv/bin/python -m src.uploaders.interactive_uploader
```

That's it. Never run setup again unless you delete `.venv/`.

---

## How the whole system works

```
┌─────────────────────────────────────────────────────┐
│  Drop raw video in yt_inbox/inputs/                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  WATCHER — Auto-detects & processes new videos      │
│  Outputs → yt_inbox/outputs/                       │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  AUTO-UPLOAD — Runs on boot + every 24 hours       │
│  Queues videos in upload_queue/                      │
└─────────────────────────────────────────────────────┘
```

---

## How to Use

### 1. Drop a Video to Process

Drop your raw video in `yt_inbox/inputs/`.

The watcher automatically:
- Detects new video
- Processes through 8-step pipeline
- Saves output to `yt_inbox/outputs/<video_name>/`
- Moves original to `yt_inbox/processed/`
- Skips videos already in `yt_inbox/outputs/`

### 2. Queue for Upload

Move the processed folder to `upload_queue/`. Folder must contain:
- `final_video_mixed.mp4` or `final_video_simple.mp4`
- `script.txt`

### 3. Auto-Upload Happens Automatically

- **On every Mac boot/login**
- **Every 24 hours**
- **One video per day**
- After upload, folder moves to `uploaded/`

---

## Manual Upload

```bash
.venv/bin/python -m src.uploaders.interactive_uploader
```

---

## Folder Structure

```
youtube_automation/
├── pipeline.py              # Run manually to process a video
├── requirements.txt         # All Python dependencies
├── config.py                # ALL settings live here
│
├── yt_inbox/               # ← DROP VIDEOS HERE
│   ├── inputs/             # Raw videos
│   ├── outputs/           # Processed videos
│   │   └── <video_name>/
│   │       ├── final_video_mixed.mp4   # Original + TTS audio
│   │       ├── final_video_simple.mp4  # TTS only
│   │       └── script.txt
│   ├── processed/          # Original videos after processing
│   └── failed/            # Videos that failed processing
│
├── upload_queue/           # Videos ready for upload
│   └── <video_name>/
├── uploaded/              # Successfully uploaded
│
├── src/
│   ├── config.py
│   ├── upload_config.py
│   ├── watcher.py         # Auto-detects & processes new videos
│   ├── steps/            # 8 pipeline steps
│   └── uploaders/        # YouTube & Instagram uploaders
│
├── scripts/
│   └── auto_service.sh   # Auto-upload on boot
│
├── logs/
│   ├── pipeline.log
│   ├── yt_upload.log
│   ├── ig_upload.log
│   └── error.log
│
└── .venv/                # Python environment (Python 3.14)
```

---

## Commands

```bash
# Run watcher (auto-processes new videos)
.venv/bin/python -m src.watcher

# Process a video manually
.venv/bin/python pipeline.py /path/to/video.mp4

# Run pipeline with TTS instead of ACE music
.venv/bin/python pipeline.py --use-tts /path/to/video.mp4

# Auto-upload (runs automatically on boot)
bash scripts/auto_service.sh

# Manual upload
.venv/bin/python -m src.uploaders.interactive_uploader
```

---

## Linting & Type Checking

```bash
# Lint
.venv/bin/ruff check .

# Type check
.venv/bin/mypy .
```

---

## Logging

```bash
tail -f logs/pipeline.log
tail -f logs/yt_upload.log
tail -f logs/error.log
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `venv not found` error | Run `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| Ollama connection refused | Run `ollama serve` in a terminal |
| YouTube auth fails | Delete `youtube_token.pickle` and re-run upload |
| Auto-upload not running | Check `logs/error.log` |
| Video not processing | Make sure it's in `yt_inbox/inputs/` (not subfolders) |
| Video re-processed | Already in `yt_inbox/outputs/` - watcher skips it |

---

## Requirements

- Python 3.14
- FFmpeg (install via `brew install ffmpeg`)
- Ollama running locally with models:
  - `qwen3.5:0.8b` (vision)
  - `qwen3.5:9b` (LLM)