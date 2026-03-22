# AGENTS.md - YouTube Automation Project

## Project Overview

Python video processing pipeline that transforms raw videos into narrated, subtitled YouTube Shorts. Uses Ollama (vision/LLM), Faster-Whisper (transcription), Chatterbox-TTS (voice), and FFmpeg.

## Environment Setup

```bash
source .venv/bin/activate
.venv/bin/python <script.py>
```

## Build / Lint / Test Commands

### Linting (Ruff)
```bash
ruff check .
ruff check . --fix
```

### Running the Pipeline
```bash
.venv/bin/python pipeline.py /path/to/video.mp4
```

### Running Individual Steps
```bash
.venv/bin/python src/steps/step1_extract_frames.py --video-file input.mp4 --interval 2.0 --output-dir yt_inbox/outputs/frames
.venv/bin/python src/steps/step2_qwen_vl.py --manifest manifest.json --model qwen3-vl:2b --prompt "..." --output-file frames.txt --context-window 5
.venv/bin/python src/steps/step3_transcribe_original.py --video input.mp4 --output transcript.txt --model base
.venv/bin/python src/steps/step4_llm_script.py --input frames.txt --output script.txt --duration 60.0 --wps 3
.venv/bin/python src/steps/step5_tts.py --script script.txt --output voice.wav --ref-audio samples/me.mp3
.venv/bin/python src/steps/step6_merge_av.py --video input.mp4 --audio voice.wav --output video_tts.mp4
.venv/bin/python src/steps/step7_transcribe_subtitles.py --video video_tts.mp4 --srt subtitles.srt --model base
.venv/bin/python src/steps/step8_burn_subtitles.py video_tts.mp4 subtitles.srt -o final_video.mp4
```

### Upload Commands
```bash
.venv/bin/python src/uploaders/interactive_uploader.py
.venv/bin/python src/uploaders/yt_uploader.py <folder>
```

### Watching Logs
```bash
tail -f logs/pipeline.log
tail -f logs/auto_upload.log
```

## Code Style Guidelines

### Imports
- Standard library first, then third-party, then local
- Explicit relative imports (`from src import config`)
- Alphabetize within groups

### Formatting
- Max line length: 100 characters
- 4 spaces for indentation (no tabs)
- Trailing commas in multi-line structures
- f-strings for string formatting

### Type Hints
- Required for all function signatures
- Use `Optional[X]` instead of `X | None`
- Example: `def extract_frames(video_path: str, interval_sec: float, output_dir: str) -> str:`

### Naming Conventions
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private functions: prefix with underscore

### Error Handling
- Explicit exception types with descriptive messages
- Catch specific exceptions when possible
- Example: `raise Exception(f"Error opening video file: {video_path}")`

### Docstrings
- Google-style for complex functions
- Put main execution behind `if __name__ == "__main__":`

### Logging
- `print()` for user-facing output
- `src.logger` module for file logging

### File Paths
- `os.path.join()` for concatenation
- `pathlib.Path` for modern handling
- Use config values (e.g., `config.PROJECT_ROOT`)

## Project Structure

```
youtube_automation/
├── pipeline.py              # Main orchestration
├── src/
│   ├── config.py           # Pipeline settings
│   ├── logger.py           # Logging utilities
│   ├── upload_config.py    # Upload platform routing
│   ├── watcher.py          # Auto-detect & process videos
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
│       ├── yt_uploader.py, ig_uploader.py
│       ├── yt_worker.py, ig_worker.py
│       └── interactive_uploader.py
├── yt_inbox/               # Drop videos here
├── upload_queue/           # Pending uploads
├── uploaded/              # Successfully uploaded
├── logs/                   # Application logs
├── samples/                # TTS reference audio
└── .venv/                  # Python virtual environment
```

## External Dependencies

- **Ollama**: Must be running (`ollama serve`) for vision/LLM
- **FFmpeg**: Required (`brew install ffmpeg`)
- **Google Cloud**: YouTube API credentials in `client_secret.json`
- **Instagram**: Session auth (`ig_session.json`)

## Common Development Tasks

### Adding a New Pipeline Step
1. Create `src/steps/stepN_name.py`
2. Add argparse CLI argument parsing
3. Output to configured output directory
4. Update `pipeline.py`

### Debugging a Failed Step
1. Check `logs/pipeline.log`
2. Run step individually with verbose output
3. Verify Ollama: `ollama list`
4. Check `yt_inbox/outputs/<video_name>/`

### Switching YouTube Channels
1. Replace `client_secret.json` with new account's OAuth credentials
2. Delete `youtube_token.pickle` if exists
3. Run upload - it will re-prompt for authorization

### Configuration
- `src/config.py` - all pipeline settings
- `src/upload_config.py` - upload platform routing
- Environment variables via `.env`
