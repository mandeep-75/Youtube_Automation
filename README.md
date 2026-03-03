# Full YT Automation Pipeline

Automated pipeline that takes a raw video and produces a fully subtitled,
voice-over narrated YouTube-ready output.

---

## Pipeline Overview

```
Video input
   │
   ├─ Step 1a  Extract frames          (chatterbox venv – OpenCV)
   ├─ Step 1b  Describe frames         (fastvlm conda env – LLaVA)
   ├─ Step 2   Generate script         (chatterbox venv – LLM)
   ├─ Step 3   Text-to-speech          (chatterbox venv – ChatterboxTTS)
   ├─ Step 3.5 Merge TTS audio + video (faster_whisper venv – ffmpeg)
   └─ Step 4   Transcribe + subtitles  (faster_whisper venv – faster-whisper + MoviePy)
                    │
                    └─► outputs/final_video.mp4  +  outputs/subtitles.srt
```

---

## Environments

| Environment | Location | Purpose |
|---|---|---|
| `fastvlm` | conda env (miniforge) | FastVLM / LLaVA frame description |
| `chatterbox` | `venvs/chatterbox/` | Frame extraction (cv2), LLM, ChatterboxTTS |
| `faster_whisper` | `venvs/faster_whisper/` | Transcription (faster-whisper) + subtitle burning |

---

## Quick Start


### 1. install fastvlm models (one-time)
```bash
bash fastvlm_install_models.sh
```

### 2. Set up the Python venvs (one-time)
```bash
bash setup_all_venvs.sh    # script will wipe & recreate any existing venvs and also rebuild the 'fastvlm' conda environment
```

The script now directly creates the two environments from the requirement
files (`requirements_chatterbox.txt` and `requirements_whisper.txt`) and
always starts from a clean state. Re-run the command if you ever need to
rebuild the venvs.

> ⚠️ **Python 3.11 required.** `chatterbox-tts` depends on features only
> available in 3.11. The bootstrap script will search for a suitable
> interpreter (e.g. `python3.11`, `python3` or `python`) and will abort if
> none of them report 3.11.  On macOS you can install it via:
> `brew install python@3.11`.

### 3. Run the full pipeline
```bash
python pipeline.py <your_video.mp4>
```

Outputs:
- `outputs/final_video.mp4`    — subtitled final video
- `outputs/video_with_tts.mp4` — video with TTS audio (merged)
- `outputs/subtitles.srt`      — SRT subtitle file
- `outputs/voice.wav`          — ChatterboxTTS voice-over
- `outputs/script.txt`         — Generated narration script
- `outputs/frames.txt`         — Frame descriptions

---

## Run merge TTS audio + video standalone

```bash
venvs/faster_whisper/bin/python src/merge_audio_video.py \
    --video  input.mp4 \
    --audio  outputs/voice.wav \
    --output outputs/video_with_tts.mp4
```

---

## Run transcription + subtitles standalone

```bash
# Transcribe a video and burn subtitles onto it
venvs/faster_whisper/bin/python src/transcribe_subtitles.py \
    --video  my_video.mp4 \
    --output my_video_subtitled.mp4 \
    --model  base \
    --srt    my_subtitles.srt

# Available model sizes (larger = more accurate, slower):
#   tiny | base | small | medium | large-v2 | large-v3
```

---

## Run TTS standalone

```bash
venvs/chatterbox/bin/python src/tts_generate.py \
    --script outputs/script.txt \
    --output outputs/voice.wav
```

---

## Project Structure

```
Full_yt_automation/
├── pipeline.py                  # Orchestrates all steps
├── setup_all_venvs.sh           # One-command venv builder
├── src/
│   ├── extract_frames.py        # Frame extraction (cv2)
│   ├── fastvlm_describe.py      # FastVLM frame descriptions
│   ├── llm_script.py            # LLM narration script generation
│   ├── tts_generate.py          # ChatterboxTTS voice-over
│   ├── merge_audio_video.py     # Merges TTS audio with video
│   ├── add_subtitles.py         # (legacy) static subtitle overlay
│   └── transcribe_subtitles.py  # faster-whisper transcription + subtitle burn
├── venvs/
│   ├── faster_whisper/
│   │   ├── requirements.txt
│   │   └── setup.sh
│   └── chatterbox/
│       ├── requirements.txt
│       └── setup.sh
├── checkpoints/                 # FastVLM model weights (not committed)
└── outputs/                     # All generated files (not committed)
```
