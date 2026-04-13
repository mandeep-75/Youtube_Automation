# AGENTS.md — YouTube Automation Pipeline

## Project Overview
Python-based video processing pipeline that converts raw videos into narrated, subtitled YouTube Shorts with auto-upload. Located at `/Users/mandeep/development/youtube_automation`.

## Build / Lint / Test Commands

```bash
# Python environment (always use this venv)
.venv/bin/python

# Linting
.venv/bin/ruff check .

# Type checking
.venv/bin/mypy .

# Run full pipeline manually
.venv/bin/python pipeline.py /path/to/video.mp4

# Run with debug mode (limits frames, faster testing)
.venv/bin/python pipeline.py --debug /path/to/video.mp4

# Run a single step
.venv/bin/python -m src.steps.step1_extract_frames --video-file video.mp4 --interval 2.0 --output-dir outputs/frames

# Note: Pipeline steps use config.PIPELINE_PYTHON interpreter

# Watch logs
tail -f logs/pipeline_YYYYMMDD.log
```

No pytest configuration exists. Tests are not yet set up.

## Code Style Guidelines

### Python Version & Environment
- Python 3.x via `.venv` (located at `.venv/bin/python`)
- All dependencies in `requirements.txt` (unified venv approach)

### Formatting
- 4-space indentation
- snake_case for functions and variables
- PascalCase for classes
- Max line length: ~100 characters (wrap when practical)

### Imports
Standard library first, then third-party, then local:
```python
import os
import argparse
import json
from datetime import timedelta

import cv2
from tqdm import tqdm

from src.config import PROJECT_ROOT
```

### Type Hints
Use type hints for function parameters and return values:
```python
def extract_frames(video_path: str, interval_sec: float, output_dir: str) -> str:
def detect_hallucination(client, image_path, model, description: str) -> tuple[bool, str]:
```
Use `Optional[X]` from `typing` when a parameter can be `None`.

### Docstrings
Include docstrings for public functions and complex logic:
```python
def detect_hallucination(client, image_path, model, description: str) -> tuple[bool, str]:
    """
    Verify a frame description against the image to detect hallucinations.
    
    Returns:
        Tuple of (is_hallucinated: bool, corrected_description: str)
    """
```

### Error Handling
- Use specific exception types when possible
- Include context in error messages:
```python
raise Exception(f"Error opening video file: {video_path}")
except Exception as e:
    print(f"\n⚠️ Hallucination check failed: {e}")
    return False, description
```

### CLI Scripts
- Use `argparse` with `--long-form` arguments
- Use `action="store_true"` for boolean flags
- Provide help text for all arguments

### Logging & Output
- Use `tqdm` for progress bars in batch processing
- Use emoji prefix for console status messages (e.g., `🚀`, `✅`, `⚠️`, `🔍`)
- Flush print output when streaming: `print(..., flush=True)`

### File Paths
- Use `os.path` for path operations (not `pathlib`)
- Use `os.path.join()` to construct paths
- Use `exist_ok=True` for `os.makedirs()`
- Define `PROJECT_ROOT` in config and use relative paths from there

### Configuration
- All settings centralized in `src/config.py`
- Use `os.environ.get("KEY", default)` for environment variables
- Load `.env` with `python-dotenv` in config

## Project Structure

```
youtube_automation/
├── pipeline.py             # Main entry point for video processing
├── src/
│   ├── config.py           # All settings (edit this file)
│   ├── upload_config.py    # Upload routing configuration
│   ├── watcher.py          # Auto-detects & processes new videos
│   ├── utils/              # Shared utilities
│   │   ├── ffmpeg.py       # FFmpeg detection helpers
│   │   └── logger.py       # Logging utilities
│   ├── steps/              # 8-step pipeline
│   │   ├── step1_extract_frames.py
│   │   ├── step2_qwen_vl.py
│   │   ├── step3_transcribe_original.py
│   │   ├── step4_llm_script.py
│   │   ├── step5_mlx_tts.py        # MLX Qwen3-TTS (voice only)
│   │   ├── step5_ace_music.py     # ACE-Step 1.5 (vocals + music)
│   │   ├── step6_merge_av.py
│   │   ├── step7_transcribe_subtitles.py
│   │   └── step8_burn_subtitles.py
│   └── uploaders/          # YouTube & Instagram uploaders
├── yt_inbox/              # Drop raw videos here (watched by watcher.py)
│   ├── outputs/            # Processed videos (auto-created)
│   │   └── <video_name>/
│   ├── processed/           # Original videos after processing
│   └── failed/             # Videos that failed
├── upload_queue/           # Videos ready for upload
├── uploaded/              # Successfully uploaded videos
├── logs/                   # Pipeline logs (pipeline_YYYYMMDD.log)
├── fonts/                  # Subtitle font files (TTF)
├── samples/                # TTS reference audio (me.mp3)
├── tools/                  # Local tools (ffmpeg)
└── requirements.txt        # All dependencies
```

## Key Dependencies
- **Vision**: `ollama`, `qwen3.5:0.8b` model
- **Transcription**: `faster-whisper` (base model)
- **TTS**: `mlx-audio` (MLX Qwen3-TTS for Apple Silicon)
- **Video**: `opencv-python`, `Pillow`, `imageio-ffmpeg`
- **Upload**: `google-api-python-client`, `instagrapi`
- **LLM**: `ollama` with `qwen3.5:9b` model

## External Services
- Ollama runs locally at `http://localhost:11434`
- YouTube API credentials in `client_secret.json`
- Instagram credentials via environment variables

## Common Patterns

### Frame Processing Loop
```python
for entry in tqdm(entries, desc="Describing Frames"):
    image_path = entry["path"]
    timestamp = entry["timestamp"]
    # ... process
```

### Manifest-Based Pipelines
Steps communicate via JSON manifests in output directories:
```python
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2)
```

### Streaming LLM Responses
```python
stream = client.generate(model=model, prompt=prompt, images=[image_path], stream=True)
response_text = []
for chunk in stream:
    token = chunk.get("response", "")
    if token:
        response_text.append(token)
result = "".join(response_text).strip()
```

## Agent-Specific Notes

### Import Style
Always use `from src import config` in step scripts—not `from config import`:
```python
# ✅ Correct (used throughout project)
from src import config

# ❌ Wrong (will fail at runtime)
from config import SOME_VAR
```

### Debug Mode
Two ways to enable:
- CLI flag: `python pipeline.py --debug video.mp4`
- Config: set `DEBUG_MODE = True` in `src/config.py`

### Output Filenames
Pipeline creates `final_video_ace.mp4` or `final_video_tts.mp4` (not `mixed`/`simple`).

### Config Matters
- `FRAME_INTERVAL` defaults to 2.0 seconds
- `DEBUG_MAX_FRAMES` limits extracted frames in debug mode (currently 2)
- `USE_ACE_MUSIC` toggles between ACE-Step (True) and MLX TTS (False)
- `DEBUG_MODE` enabled by default for faster testing
