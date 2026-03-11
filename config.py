# config.py
# ─────────────────────────────────────────────────────────────────────────────
# ⚙️  PIPELINE SETTINGS
# Edit this file to customise every aspect of the pipeline.
# pipeline.py imports everything from here — you never need to touch it.
# ─────────────────────────────────────────────────────────────────────────────

import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────────────────────────
# 0. GLOBAL / COMMON SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"


# ─────────────────────────────────────────────────────────────────────────────
# 1. FRAME EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

FRAME_INTERVAL = "1.0"          # seconds between extracted frames (lower = more frames)

# ─────────────────────────────────────────────────────────────────────────────
# 2. VISION MODEL  — visual frame description (via Ollama)
# ─────────────────────────────────────────────────────────────────────────────

VISION_MODEL  = "qwen3-vl:2b" # Model name in Ollama

VISION_PROMPT = """You are analyzing a single frame from a video.

Describe the frame in **one detailed and descriptive sentence** that clearly includes the following elements in order: the **main subject**, the **action being performed**, the **foreground elements (objects closest to the camera)**, and the **background environment or distant elements**.

Guidelines:
- Base the description strictly on **visible facts** in the image.
- **Do not speculate** about emotions, identities, intentions, or events outside the frame.
- Clearly distinguish between the **main subject**, **foreground**, and **background**.
- Mention notable **people, animals, objects, vehicles, text, or structures** if visible.
- Include **important visual details** such as clothing, colors, posture, lighting, setting, and spatial relationships when relevant.
- Use **neutral and objective language**.
- The sentence should be **detailed but still clear and readable**.
- Avoid repeating words unnecessarily.

Output requirement:
Return **one single, detailed sentence only** that naturally describes the frame while including the subject, action, foreground, and background in that order.
"""



# ─────────────────────────────────────────────────────────────────────────────
# 3. WHISPER  — used in Step 3 (original audio) and Step 7 (TTS subtitles)
# ─────────────────────────────────────────────────────────────────────────────

WHISPER_MODEL        = "base"          # tiny | base | small | medium | large-v3
WHISPER_LANG         = None            # e.g. "en" to force English, or None for auto-detect
WHISPER_BEAM_SIZE    = 5
WHISPER_COMPUTE_TYPE = "int8"          # int8 | float16 | float32


# ─────────────────────────────────────────────────────────────────────────────
# 4. LLM SCRIPT  — Ollama model for narration script generation
# ─────────────────────────────────────────────────────────────────────────────

# LLM_MODEL = "qwen3.5:9b"       # any model installed in your local Ollama instance

LLM_MODEL = "jaahas/qwen3.5-uncensored:9b"

# ─────────────────────────────────────────────────────────────────────────────
# 5. TTS  — Chatterbox voice synthesis
# ─────────────────────────────────────────────────────────────────────────────

TTS_REF_AUDIO = [
    "./samples/me.mp3",
    "./samples/me2.mp3"
]   # reference voice clip(s). if a list is provided, one will be chosen randomly.

# Voice characteristics
TTS_EXAGGERATION      = 0.6
TTS_TEMPERATURE       = 0.05
TTS_CFG_WEIGHT        = 0.5
TTS_REPETITION_PENALTY = 1.2


# ─────────────────────────────────────────────────────────────────────────────
# 6. MERGE  — how TTS audio is mixed with the original video audio
# ─────────────────────────────────────────────────────────────────────────────

# enabling this may cause copyright issues
MERGE_MIX_AUDIO = False         # True  = mix TTS + original audio together
                                # False = replace original audio with TTS only

ORIGINAL_AUDIO_VOLUME = 0.4    # 0.0 to 1.0 (e.g., 0.1 = 10% volume)
                                # Only used if MERGE_MIX_AUDIO is True.


# ─────────────────────────────────────────────────────────────────────────────
# 7 & 8. SUBTITLES  — burn-in styling
# ─────────────────────────────────────────────────────────────────────────────

# CUSTOM SHORTS FONTS (Local TTF files in fonts/ directory):
# Anton natively renders smaller than other fonts, so we give it a larger size to match visually.
SUBTITLE_FONTS = [
    {"name": "Anton", "size": 120},
    {"name": "Bebas Neue", "size": 120},
    {"name": "Oswald", "size": 120}
]
SUBTITLE_FONT_COLOR     = "#FFFFFF"
SUBTITLE_HIGHLIGHT_COLOR = "#00FFAA"
SUBTITLE_OUTLINE_COLOR   = "#000000"
SUBTITLE_OUTLINE_WIDTH   = 1
SUBTITLE_MAX_WORDS      = 3
SUBTITLE_BOLD           = True
SUBTITLE_ITALIC         = False
SUBTITLE_POSITION       = "center" # top, center, bottom
SUBTITLE_X_OFFSET       = -50
SUBTITLE_Y_OFFSET       = 250



# ─────────────────────────────────────────────────────────────────────────────
# PYTHON INTERPRETERS  — one per virtual environment
# Only change if your conda / venv paths differ from the defaults.
# ─────────────────────────────────────────────────────────────────────────────


CHATTERBOX_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "chatterbox", "bin", "python")

FASTER_WHISPER_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "faster_whisper", "bin", "python")

UPLOADER_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "uploader", "bin", "python")
