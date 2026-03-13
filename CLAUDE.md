# CLAUDE.md

This file provides guidance to Claude Code when working with this YouTube automation project. Focus on workflow, dependencies, and architecture.

## Common Commands
- **Process video**: `python pipeline.py /path/to/raw_video.mp4`
  *Runs all 8 automated steps: frame extraction → vision analysis → audio transcription → script generation → TTS → video synthesis → final upload prep*
- **Manual upload**: `venvs/uploader/bin/python youtube_upload.py`
  *Interactive menu to select video from `outputs/` and upload to YouTube*
- **Auto-upload setup**:
  1. Move `final_video.mp4` + `script.txt` to `upload_queue/`
  2. Reboot or run `launchctl start com.mandeep.youtube_autoupload`
- **Environments**:
  - First-time setup: `bash setup_all_venvs.sh`
  - Reinstall: Delete `venvs/` folder and re-run setup

## Core Architecture
1. **Video Pipeline (`pipeline.py`)**:
   - Orchestrates 8 steps through:
     - **Ollama models** (Qwen3-VL for frame analysis, LLM for script generation)
     - **Faster-Whisper** for audio transcription
     - **Chatterbox-TTS** for voice generation
   - Outputs final video with subtitles in `outputs/`

2. **AI Workflow**:
   - **Script Generation**: Uses Ollama (`jaahas/qwen3.5-uncensored:9b`) to create narration from frame descriptions and optional audio transcripts
   - **Custom Tone**: Narration follows cinematic, story-driven style with "This man..." openings

3. **Upload System**:
   - Manual: `youtube_upload.py` selects videos from `outputs/`
   - Auto: Daily uploads from `upload_queue/` (via launchd service)
   - Links processed videos to YouTube account via `youtube_token.pickle`

## Key Configuration
- **`config.py`**: Central control for all parameters
  - Controls:
    - Target word count (based on video duration × WPS)
    - LLMs used for script generation
    - Upload scheduling rules

## Folder Structure Reference
```
youtube_automation/
├── pipeline.py              # Main video processing workflow
├── youtube_upload.py        # Manual upload interface
├── config.py                # All runtime settings
├── outputs/                 # Final videos + scripts
│   └── your_video_name/     # Contains final_video.mp4 + script.txt
├── upload_queue/            # Auto-upload folder (drop here)
├── venvs/                   # Python environments (auto-managed)
│   ├── chatterbox/          # TTS model
│   └── faster_whisper/      # Audio transcription
```

## Developer Notes
- Always move processed videos to `upload_queue/` for auto-upload
- Never modify `venvs/` directly - use `setup_all_venvs.sh` for changes
- Use `config.py` to adjust outputs without code changes
- Check `autoupload_log` for errors if uploads fail