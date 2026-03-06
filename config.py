# config.py
# ─────────────────────────────────────────────────────────────────────────────
# ⚙️  PIPELINE SETTINGS
# Edit this file to customise every aspect of the pipeline.
# pipeline.py imports everything from here — you never need to touch it.
# ─────────────────────────────────────────────────────────────────────────────

import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────────────────────────
# 1. FRAME EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

FRAME_INTERVAL = "2.0"          # seconds between extracted frames (lower = more frames)


# ─────────────────────────────────────────────────────────────────────────────
# 2. FASTVLM  — visual frame description
# ─────────────────────────────────────────────────────────────────────────────

FASTVLM_MODEL_PATH = os.path.join(
    PROJECT_ROOT, "checkpoints", "llava-fastvithd_1.5b_stage3"
)

# Prompt sent to FastVLM for every frame (do NOT include <image> — added automatically)
FASTVLM_PROMPT = "Describe what is happening in this frame in two sentences."


# ─────────────────────────────────────────────────────────────────────────────
# 3. WHISPER  — used in Step 3 (original audio) and Step 7 (TTS subtitles)
# ─────────────────────────────────────────────────────────────────────────────

WHISPER_MODEL = "base"          # tiny | base | small | medium | large-v3
WHISPER_LANG  = None            # e.g. "en" to force English, or None for auto-detect


# ─────────────────────────────────────────────────────────────────────────────
# 4. LLM SCRIPT  — Ollama model for narration script generation
# ─────────────────────────────────────────────────────────────────────────────

LLM_MODEL = "qwen3.5:9b"       # any model installed in your local Ollama instance


# ─────────────────────────────────────────────────────────────────────────────
# 5. TTS  — Chatterbox voice synthesis
# ─────────────────────────────────────────────────────────────────────────────

TTS_REF_AUDIO = "./samples/1.mp3"   # reference voice clip (short, clear speech)


# ─────────────────────────────────────────────────────────────────────────────
# 6. MERGE  — how TTS audio is mixed with the original video audio
# ─────────────────────────────────────────────────────────────────────────────

MERGE_MIX_AUDIO = False         # True  = mix TTS + original audio together
                                # False = replace original audio with TTS only


# ─────────────────────────────────────────────────────────────────────────────
# 7 & 8. SUBTITLES  — burn-in styling
# ─────────────────────────────────────────────────────────────────────────────

SUBTITLE_FONT_NAME    = "Arial"
SUBTITLE_FONT_SIZE    = "24"
SUBTITLE_FONT_COLOR   = "#FFFFFF"    # text colour (white)
SUBTITLE_BORDER_COLOR = "#000000"    # outline colour (black)
SUBTITLE_BORDER_WIDTH = "2"
SUBTITLE_MAX_WORDS    = "3"          # words visible on screen at once


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON INTERPRETERS  — one per virtual environment
# Only change if your conda / venv paths differ from the defaults.
# ─────────────────────────────────────────────────────────────────────────────

FASTVLM_PYTHON = "/opt/homebrew/Caskroom/miniforge/base/envs/fastvlm/bin/python"

CHATTERBOX_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "chatterbox", "bin", "python")

FASTER_WHISPER_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "faster_whisper", "bin", "python")
