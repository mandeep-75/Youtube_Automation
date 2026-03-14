# AGENTS.md - Agent Coding Guidelines

This file provides guidelines for AI agents working in this YouTube automation repository.

## 1. Build and Run Commands

### Running the Pipeline

```bash
# Process a video through the full 8-step pipeline
.venv/unified/bin/python pipeline.py /path/to/video.mp4

# Process multiple videos
.venv/unified/bin/python pipeline.py video1.mp4 video2.mp4
```

### Virtual Environment

All Python commands should use the unified venv:
```bash
.venv/unified/bin/python <script>
```

## 2. Code Style Guidelines

### General Conventions

- **Language**: Python 3.11+
- **Style**: Follow PEP 8 with snake_case naming
- **Type hints**: Use for function signatures (especially in library code)
- **Docstrings**: Use Google-style docstrings for public functions

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Functions/variables | snake_case | `extract_frames`, `video_path` |
| Classes | PascalCase | `PipelineLogger`, `TestStep1` |
| Constants | UPPER_SNAKE_CASE | `OLLAMA_URL`, `FRAME_INTERVAL` |
| Private functions | prefix with underscore | `_format_ts` |

### Import Organization

Order imports as follows (within each group, alphabetically):
1. Standard library (`os`, `sys`, `argparse`)
2. Third-party packages (`cv2`, `json`)
3. Local imports (`from src import config`)

```python
import os
import sys
import argparse
import json

import cv2
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src import config
from src.logger import PipelineLogger
```

### File Structure

```
youtube_automation/
├── pipeline.py              # Main pipeline entry point
├── AGENTS.md               # This file
├── README.md               # Project documentation
├── .env                    # Environment variables
├── client_secret.json      # YouTube API credentials
├── youtube_token.pickle   # YouTube auth token
├── ig_session.json        # Instagram session
├── requirements.txt       # Python dependencies
│
├── src/
│   ├── __init__.py
│   ├── config.py          # All settings (imported by pipeline)
│   ├── logger.py          # Centralized logging
│   ├── watcher.py         # File watcher
│   │
│   ├── steps/             # Pipeline step implementations
│   │   ├── step1_extract_frames.py
│   │   ├── step2_qwen_vl.py
│   │   ├── step3_transcribe_original.py
│   │   ├── step4_llm_script.py
│   │   ├── step5_tts.py
│   │   ├── step6_merge_av.py
│   │   ├── step7_transcribe_subtitles.py
│   │   └── step8_burn_subtitles.py
│   │
│   └── uploaders/         # Upload workers
│       ├── yt_worker.py
│       ├── ig_worker.py
│       └── interactive_uploader.py
│
├── scripts/               # Shell scripts
│   ├── yt_service.sh
│   └── ig_service.sh
│
├── tools/                # Binary tools (ffmpeg, ffprobe)
├── fonts/               # Subtitle font files (TTF)
├── samples/             # Reference audio samples
├── docs/                 # Documentation
├── logs/                 # Log files
├── outputs/              # Processed video output
├── upload_queue/         # Videos waiting for upload
└── uploaded/             # Successfully uploaded videos
```

### Logging

- Use the centralized logger from `src/logger.py`
- Use `PipelineLogger` for pipeline steps (automatically logs to error.log)
- Use print statements only for CLI tools and user-facing output

```python
from src.logger import PipelineLogger

logger = PipelineLogger("step1")
logger.info("Extracting frames...")
logger.error("Failed to extract frames")
```

### Argument Parsing

Use `argparse` for CLI scripts:

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, default="output.txt")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
```

### Error Handling

- Raise exceptions with descriptive messages
- Use try/except for recoverable errors
- Log errors before re-raising

```python
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    raise Exception(f"Error opening video file: {video_path}")
```

### Configuration

All settings belong in `src/config.py`. Never hardcode values:
- API URLs, model names
- File paths (use `PROJECT_ROOT` for base paths)
- Thresholds, intervals, sizes
- Credentials via environment variables (use `.env`)

```python
# Good
output_dir = os.path.join(config.PROJECT_ROOT, "outputs")

# Bad
output_dir = "/Users/mandeep/development/youtube_automation/outputs"
```

### Video Processing Patterns

- Always create output directories with `os.makedirs(dir, exist_ok=True)`
- Use manifest files (JSON) to track generated artifacts
- Log progress with step names for debugging

## 3. Project-Specific Notes

### Pipeline Steps

| Step | Description | Key Dependencies |
|------|-------------|-------------------|
| 1 | Extract frames | OpenCV |
| 2 | Vision description | Ollama (Qwen3-VL) |
| 3 | Transcribe original | faster-whisper |
| 4 | Generate script | Ollama (LLM) |
| 5 | Text-to-speech | chatterbox |
| 6 | Merge audio/video | FFmpeg |
| 7 | Transcribe TTS | faster-whisper |
| 8 | Burn subtitles | FFmpeg |

### Output Directory Structure

Each processed video creates a folder in `outputs/`:
```
outputs/<video_name>/
├── frames/              # Extracted frames
│   └── manifest.json
├── frames.txt          # Vision descriptions
├── transcript.txt       # Original audio transcription
├── script.txt          # Generated narration script
├── voice.wav           # TTS audio output
├── video_with_tts.mp4  # Video with TTS (before subtitles)
├── subtitles.srt       # Subtitle file
└── final_video.mp4      # Final output with burned subtitles
```

### Upload Queue

Videos waiting for upload go in `upload_queue/` with structure:
```
upload_queue/<video_folder>/
├── final_video.mp4   (required)
├── script.txt        (required)
├── youtube_id.txt    (added after YT upload)
└── ig_id.txt         (added after IG upload)
```

### Logs

- `logs/pipeline.log` - Video processing
- `logs/yt_upload.log` - YouTube uploads
- `logs/ig_upload.log` - Instagram uploads
- `logs/error.log` - All errors

### Configuration Sections (src/config.py)

The config file is organized into sections:

| Section | Description |
|---------|-------------|
| 0. GLOBAL | OLLAMA_URL |
| 1. FRAME EXTRACTION | FRAME_INTERVAL |
| 2. VISION MODEL | VISION_MODEL, VISION_PROMPT |
| 3. WHISPER | WHISPER_MODEL, WHISPER_LANG, WHISPER_BEAM_SIZE, WHISPER_COMPUTE_TYPE |
| 4. LLM SCRIPT | LLM_MODEL, LLM_WORDS_PER_SECOND |
| 5. TTS | TTS_REF_AUDIO, TTS_EXAGGERATION, TTS_TEMPERATURE, TTS_CFG_WEIGHT, TTS_REPETITION_PENALTY |
| 6. MERGE | MERGE_MIX_AUDIO, ORIGINAL_AUDIO_VOLUME |
| 7 & 8. SUBTITLES | SUBTITLE_FONTS, SUBTITLE_FONT_COLOR, SUBTITLE_HIGHLIGHT_COLOR, SUBTITLE_OUTLINE_COLOR, SUBTITLE_MAX_WORDS, SUBTITLE_POSITION |
| PYTHON INTERPRETERS | UNIFIED_PYTHON, CHATTERBOX_PYTHON, FASTER_WHISPER_PYTHON, UPLOADER_PYTHON |
| 9. UPLOADER | CLIENT_SECRET_FILE, YOUTUBE_TOKEN_FILE, IG_SESSION_FILE, IG_USERNAME, IG_PASSWORD |

## 4. Environment Setup

Required services:
- **Ollama**: Run `ollama serve` before using vision/LLM steps
- **FFmpeg**: Present in `tools/` directory (or system PATH)

First-time setup:
```bash
ollama pull qwen3-vl:2b
ollama pull qwen3.5:9b
bash setup_all_venvs.sh  # or create .venv manually
```

Required environment variables (in `.env`):
- `IG_USERNAME` - Instagram username
- `IG_PASSWORD` - Instagram password

## 5. Shell Scripts

```bash
# Start YouTube upload service
bash scripts/yt_service.sh

# Start Instagram upload service
bash scripts/ig_service.sh
```
