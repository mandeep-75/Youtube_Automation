# YouTube Automation Pipeline

A modular, automated pipeline for converting raw video footage into fully narrated, subtitled, and YouTube-ready Shorts/videos.

---

## 🚀 Pipeline Overview

The pipeline executes an 8-step process to transform your video:

```
Video input
   │
   ├─ Step 1  Extract Frames           (OpenCV) - Captures visual highlights
   ├─ Step 2  Vision Analysis          (Ollama + Qwen3-VL) - Describes the action
   ├─ Step 3  Transcribe Original      (Faster-Whisper) - Captures background context
   ├─ Step 4  Generate Script          (Ollama + LLM) - Writes a viral narration script
   ├─ Step 5  Text-to-Speech           (Chatterbox-TTS) - Generates professional voice-over
   ├─ Step 6  Merge Audio + Video      (FFmpeg) - Mixes original audio + new TTS
   ├─ Step 7  Transcribe Subtitles     (Faster-Whisper) - Perfect timing for captions
   └─ Step 8  Burn Subtitles           (MoviePy/FFmpeg) - Stylish, high-engagement captions
                    │
                    └─► outputs/[video_name]/final_video.mp4
```

---

## 🛠 Prerequisites

- **macOS** (Optimized for Apple Silicon)
- **Python 3.11** (Required for Chatterbox-TTS)
- **FFmpeg** (`brew install ffmpeg`)
- **Ollama** installed and running locally
- **Ollama Models**:
  - `qwen3-vl:2b` (Vision)
  - `jaahas/qwen3.5-uncensored:9b` (LLM) — *or your preferred model*

---

## 📦 Installation

### 1. Model Setup (Ollama)
Ensure your Ollama instance is running and pull the required models:
```bash
ollama pull qwen3-vl:2b
ollama pull jaahas/qwen3.5-uncensored:9b
```

### 2. Virtual Environments
The project uses three isolated virtual environments for stability. Initialize them all with one command:
```bash
bash setup_all_venvs.sh
```

---

## 🎮 Usage

### ⚙️ Configuration
All settings (prompts, models, subtitle styles, volume levels) are centralized in `config.py`. Edit this file to customize your pipeline.

### 🎥 Run the Pipeline
Process one or more videos:
```bash
python pipeline.py path/to/video.mp4
```
Outputs are saved to `outputs/[video_name]/`.

### 📂 Watch Folder (Automatic Processing)
Monitor a directory (e.g., your Desktop) and process videos as they are dropped in:
```bash
venvs/chatterbox/bin/python src/watcher.py --watch-dir ~/Desktop/to_process --output-dir outputs
```

### 📤 YouTube Uploader
Launch an interactive menu to generate SEO metadata and upload finished videos:
```bash
venvs/uploader/bin/python youtube_upload.py
```
*Requires `client_secret.json` from Google Cloud Console.*

---

## 📁 Project Structure

```
youtube_automation/
├── config.py              # Central configuration hub
├── pipeline.py            # Main entry point (orchestrator)
├── youtube_upload.py      # Interactive uploader menu
├── setup_all_venvs.sh     # Automation setup script
├── src/
│   ├── step1_extract_frames.py
│   ├── step2_qwen_vl.py
│   ├── step3_transcribe_original.py
│   ├── step4_llm_script.py
│   ├── step5_tts.py
│   ├── step6_merge_av.py
│   ├── step7_transcribe_subtitles.py
│   ├── step8_burn_subtitles.py
│   └── watcher.py
├── venvs/                 # Isolated Python environments (gitignored)
├── samples/               # Reference audio for TTS cloning
└── outputs/               # Finished videos and intermediate logs
```

---

## 🔧 Troubleshooting

- **Python Version**: If `setup_all_venvs.sh` fails, ensure `python3.11` is in your PATH. 
- **Ollama Connection**: Ensure `OLLAMA_URL` in `config.py` matches your Ollama port (default: `11434`).
- **Curses Error**: If the uploader crashes with `addwstr()`, ensure your terminal window is sufficiently large.
