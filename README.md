# YouTube Automation Pipeline

> Turn any raw video into a narrated, subtitled, AI-voiced YouTube Short — then upload it automatically every day.

---

## ⚡ Quick Start (first time only)

```bash
# 1. Pull the two Ollama models
ollama pull qwen3-vl:2b
ollama pull jaahas/qwen3.5-uncensored:9b

# 2. Build all Python environments (one command)
bash setup_all_venvs.sh

# 3. Authenticate YouTube (opens browser once)
.venv/unified/bin/python src/uploaders/interactive_uploader.py
```

That's it. Never run setup again unless you delete `.venv/`.

---

## 🗺️ How the whole system works

```
┌─────────────────────────────────────────────────────┐
│  You have a raw video                               │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  STEP A — Process the video  (pipeline.py)          │
│  8 automated steps → final_video.mp4 in outputs/   │
└─────────────────┬───────────────────────────────────┘
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
┌──────────────┐   ┌──────────────────────────────────┐
│  MANUAL      │   │  AUTOMATIC (daily, on boot)       │
│  upload now  │   │  Drop folder → auto-uploads       │
│  (pick from  │   │  one video per day via launchd   │
│  a menu)     │   └──────────────────────────────────┘
└──────────────┘
```

---

## 🎬 Part 1 — Process a Video  (`pipeline.py`)

Drop your raw video anywhere, then run:

```bash
python pipeline.py /path/to/your_video.mp4
```

The pipeline runs **8 steps automatically**:

| Step | What it does | Tool used |
|------|-------------|-----------|
| 1 | Extract frames | OpenCV |
| 2 | Describe each frame | Ollama (Qwen3-VL vision) |
| 3 | Transcribe original audio | Faster-Whisper |
| 4 | Generate narration script | Ollama (LLM) |
| 5 | Create AI voice-over | Chatterbox-TTS |
| 6 | Merge voice onto video | FFmpeg |
| 7 | Transcribe voice for subtitles | Faster-Whisper |
| 8 | Burn subtitles onto video | FFmpeg |

**Output** → `outputs/your_video_name/final_video.mp4`

> ⚙️ Tweak anything (subtitle style, voice, LLM model, volume) in **`config.py`** — it controls everything.

---

## 📤 Part 2A — Upload Manually  (`youtube_upload.py`)

Use this when you want to pick which video to upload right now.

```bash
.venv/unified/bin/python src/uploaders/interactive_uploader.py
```

- Opens an interactive menu
- Shows all videos in `outputs/`  
- Tick mark `[OK]` = already uploaded
- Select a video → AI generates title/description/tags → uploads to YouTube

---

## 📅 Part 2B — Auto Upload Daily  (runs on boot automatically)

Use this for hands-free, one-video-per-day uploads.

### How to queue a video for upload

1. Open the **`📤 YouTube Upload Queue`** folder on your Desktop
2. Move your processed video folder (from `outputs/`) into it  
   The folder must have `final_video.mp4` and `script.txt` inside
3. That's it — the upload will happen automatically

### When does it upload?

- **On every Mac boot/login** — automatically
- **Every 24 hours** — if your Mac stays on
- **One video per day** — oldest folder in the queue goes first
- **After upload** — folder moves to `uploaded/` automatically

### Check what's happening

```bash
# Live upload log
tail -f ~/development/youtube_automation/autoupload.log

# Error log
tail -f ~/development/youtube_automation/autoupload_error.log

# Trigger manually right now
launchctl start com.mandeep.youtube_autoupload
```

---

## 📸 Part 2C — Instagram Auto Upload (runs on boot automatically)

The system also supports auto-uploading to Instagram Reels.

### How it works

- Runs automatically on boot and every 24 hours (same schedule as YouTube)
- One video per day, oldest folder in queue goes first
- After upload, folder stays in `upload_queue/` until YouTube upload is also complete
- Once both platforms have uploaded, folder moves to `uploaded/`

### Requirements

1. Add your Instagram credentials to `.env`:
   ```
   IG_USERNAME=your_username
   IG_PASSWORD=your_password
   ```

2. Queue videos the same way as YouTube (drop folder in `upload_queue/`)

### Check what's happening

```bash
# Live Instagram upload log
tail -f logs/ig_upload.log

# Trigger manually right now
launchctl start com.mandeep.ig_autoupload
```

---

## 📁 Folder Reference

```
youtube_automation/
│
├── pipeline.py              ← Run this to process a raw video
├── config.py                ← ALL settings live here (edit this)
├── setup_all_venvs.sh       ← First-time setup (run once)
│
├── src/                     ← Source code
│   ├── __init__.py
│   ├── config.py            ← Settings (imported by pipeline.py)
│   ├── logger.py            ← Centralized logging system
│   ├── steps/               ← Pipeline steps (don't need to touch)
│   │   ├── __init__.py
│   │   ├── step1_extract_frames.py
│   │   ├── step2_qwen_vl.py
│   │   ├── step3_transcribe_original.py
│   │   ├── step4_llm_script.py
│   │   ├── step5_tts.py
│   │   ├── step6_merge_av.py
│   │   ├── step7_transcribe_subtitles.py
│   │   └── step8_burn_subtitles.py
│   └── uploaders/           ← Upload workers
│       ├── __init__.py
│       ├── yt_worker.py
│       ├── ig_worker.py
│       └── interactive_uploader.py
│
├── scripts/                 ← Bash scripts for scheduled tasks
│   ├── yt_service.sh
│   └── ig_service.sh
│
├── logs/                    ← Centralized logs (rotating, auto-managed)
│   ├── pipeline.log
│   ├── yt_upload.log
│   ├── ig_upload.log
│   └── error.log
│
├── outputs/                 ← Processed videos land here
│   └── your_video_name/
│       ├── final_video.mp4  ← Upload-ready video
│       └── script.txt       ← Generated narration
│
├── upload_queue/            ← Drop folders here for auto-upload
│   └── (your video folders go here)
│
├── uploaded/                ← Moved here after successful upload
│
├── .venv/                   ← Python environments (auto-created, gitignored)
│   ├── unified/             ← Main environment (all dependencies)
│   └── ...
│
├── tools/                   ← External tools (ffmpeg binary)
├── docs/                    ← Documentation
├── tests/                   ← Test files
├── youtube_token.pickle     ← YouTube auth token
└── ig_session.json          ← Instagram session
```

---

## 📝 Logging

All logs are centralized in the `logs/` directory with automatic rotation (10MB max per file, 5 backups):

```bash
# Watch pipeline logs
tail -f logs/pipeline.log

# Watch YouTube upload logs
tail -f logs/yt_upload.log

# Watch Instagram upload logs
tail -f logs/ig_upload.log

# Watch all errors
tail -f logs/error.log
```

| Log File | What it captures |
|----------|------------------|
| `pipeline.log` | Video processing pipeline (all 8 steps) |
| `yt_upload.log` | YouTube auto-uploads |
| `ig_upload.log` | Instagram auto-uploads |
| `error.log` | All errors from all modules |

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| `venv not found` error | Run `bash setup_all_venvs.sh` |
| Ollama connection refused | Run `ollama serve` in a terminal |
| YouTube auth fails | Delete `youtube_token.pickle` and re-run upload |
| Auto-upload not running | Check `logs/error.log` |
| Curses menu crash | Make your terminal window bigger |
| Video folder not uploading | Make sure it has both `final_video.mp4` AND `script.txt` |
| Instagram login fails | Check `logs/ig_upload.log` for errors | |
