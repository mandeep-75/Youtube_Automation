# AGENTS.md - YouTube Automation Project

## Project Overview

Python-based video processing pipeline that transforms raw videos into narrated, subtitled YouTube Shorts with automatic upload capabilities. Uses Ollama for vision/LLM, Faster-Whisper for transcription, Chatterbox-TTS for voice synthesis, and FFmpeg for video processing.

## Environment Setup

```bash
# Activate the virtual environment
source .venv/bin/activate

# Or use the full path directly
.venv/bin/python <script.py>
```

## Build / Lint / Test Commands

### Running the Pipeline
```bash
# Process a video through all 8 steps
.venv/bin/python pipeline.py /path/to/video.mp4
```

### Linting (Ruff)
```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check . --fix
```

### Running Individual Steps (Debugging)
```bash
# Step 1: Extract frames
.venv/bin/python src/steps/step1_extract_frames.py --video-file input.mp4 --interval 2.0 --output-dir yt_inbox/outputs/frames

# Step 2: Vision descriptions
.venv/bin/python src/steps/step2_qwen_vl.py --manifest manifest.json --model qwen3-vl:2b --prompt "..." --output-file frames.txt --context-window 5

# Step 3: Transcribe original audio
.venv/bin/python src/steps/step3_transcribe_original.py --video input.mp4 --output transcript.txt --model base

# Step 4: Generate narration script
.venv/bin/python src/steps/step4_llm_script.py --input frames.txt --output script.txt --duration 60.0 --wps 3

# Step 5: Text-to-speech
.venv/bin/python src/steps/step5_tts.py --script script.txt --output voice.wav --ref-audio samples/me.mp3

# Step 6: Merge audio/video
.venv/bin/python src/steps/step6_merge_av.py --video input.mp4 --audio voice.wav --output video_tts.mp4

# Step 7: Transcribe TTS for subtitles
.venv/bin/python src/steps/step7_transcribe_subtitles.py --video video_tts.mp4 --srt subtitles.srt --model base

# Step 8: Burn subtitles
.venv/bin/python src/steps/step8_burn_subtitles.py video_tts.mp4 subtitles.srt -o final_video.mp4
```

### Upload Commands
```bash
# Interactive YouTube upload
.venv/bin/python src/uploaders/interactive_uploader.py

# Auto-uploader (for upload_queue/)
.venv/bin/python src/uploaders/auto_uploader.py <folder>
```

### Watching Logs
```bash
tail -f logs/pipeline.log
tail -f logs/auto_upload.log
tail -f logs/error.log
```

## Code Style Guidelines

### Imports
- Standard library imports first, then third-party, then local
- Use explicit relative imports for project modules (`from src import config`)
- Alphabetize within import groups

### Formatting
- Maximum line length: 100 characters (ruff default)
- Use 4 spaces for indentation (no tabs)
- Add trailing commas in multi-line structures
- Use f-strings for string formatting

### Type Hints
- Use type hints for all function signatures
- Common types: `str`, `int`, `float`, `bool`, `List[str]`, `Dict[str, Any]`
- Use `Optional[X]` instead of `X | None` for compatibility

### Naming Conventions
- Functions/variables: `snake_case` (e.g., `extract_frames`, `video_path`)
- Classes: `PascalCase` (e.g., `VideoProcessor`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_FRAME_COUNT`)
- Private functions: prefix with underscore (e.g., `_internal_helper`)

### Error Handling
- Use explicit exception types with descriptive messages
- Catch specific exceptions when possible

### Function Structure
- Keep functions focused and single-purpose
- Use docstrings for complex functions (Google style)
- Put main execution behind `if __name__ == "__main__":`

### Logging
- Use print statements for user-facing output (pipeline.py uses this pattern)
- Use the `src/logger.py` module for application logging to files

### File Paths
- Use `os.path.join()` for path concatenation
- Use `pathlib.Path` for modern path handling when appropriate
- Reference config values for project paths (e.g., `config.PROJECT_ROOT`)

### Pipeline Steps
- Each step is a standalone script in `src/steps/`
- Steps communicate via JSON manifest files or command-line arguments
- Return paths to output files for chaining steps

### Configuration
- All settings go in `src/config.py`
- Use environment variables via `python-dotenv` for sensitive data
- Constants at module level, runtime config can be mutable

### Video Processing Patterns
- Use subprocess to call FFmpeg for video operations
- Check return codes with `check=True` for critical operations
- Use temporary directories for intermediate outputs
- Clean up temporary files when done

## Project Structure

```
youtube_automation/
├── pipeline.py              # Main orchestration script
├── src/
│   ├── config.py           # All configuration settings
│   ├── logger.py           # Centralized logging
│   ├── watcher.py          # Auto-detects & processes new videos
│   ├── steps/              # 8 pipeline steps
│   │   ├── step1_extract_frames.py
│   │   ├── step2_qwen_vl.py
│   │   ├── step3_transcribe_original.py
│   │   ├── step4_llm_script.py
│   │   ├── step5_tts.py
│   │   ├── step6_merge_av.py
│   │   ├── step7_transcribe_subtitles.py
│   │   └── step8_burn_subtitles.py
│   └── uploaders/          # Upload workers
│       ├── yt_worker.py
│       ├── ig_worker.py
│       ├── auto_uploader.py
│       └── interactive_uploader.py
├── scripts/
│   └── auto_service.sh    # Auto-upload on boot
├── yt_inbox/               # Drop videos here
│   ├── inputs/             # Raw videos (optional)
│   ├── outputs/           # Processed videos
│   ├── processed/          # Original videos after processing
│   └── failed/            # Failed videos
├── upload_queue/           # Videos pending upload
├── uploaded/              # Successfully uploaded
├── logs/                   # Application logs
├── samples/                # Reference audio for TTS
└── .venv/                  # Python virtual environment
```

## External Dependencies

- **Ollama**: Must be running locally (`ollama serve`) for vision/LLM steps
- **FFmpeg**: Required for video processing (`brew install ffmpeg`)
- **Google Cloud**: YouTube API credentials in `client_secret.json`
- **Instagram**: Session-based authentication (ig_session.json)

## Common Development Tasks

### Adding a New Pipeline Step
1. Create `src/steps/stepN_name.py`
2. Add CLI argument parsing with argparse
3. Output results to configured output directory
4. Update `pipeline.py` to call the new step

### Modifying Configuration
Edit `src/config.py` - all pipeline settings are centralized there.

### Debugging a Failed Step
1. Check logs in `logs/pipeline.log`
2. Run the step individually with verbose output
3. Verify Ollama is running: `ollama list`
4. Check intermediate outputs in `yt_inbox/outputs/<video_name>/`

### Running the Watcher
```bash
# Option 1: Run directly
.venv/bin/python src/watcher.py

# Option 2: Use the script
bash scripts/watch.sh

# Option 3: Double-click watcher.command on Desktop
```
