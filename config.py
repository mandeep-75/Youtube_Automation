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

FRAME_INTERVAL = "2.0"          # seconds between extracted frames (lower = more frames)

# ─────────────────────────────────────────────────────────────────────────────
# 2. VISION MODEL  — visual frame description (via Ollama)
# ─────────────────────────────────────────────────────────────────────────────

VISION_MODEL  = "qwen3-vl:2b" # Model name in Ollama

VISION_PROMPT = "Describe this frame in one sentence."

# VISION_PROMPT = """Describe the actions happening in this image.
#                 Explain what the people or animals are doing .
#                 Focus on activities, tasks, and interactions.
#                 Write 2 clear sentences."""



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

LLM_MODEL = "qwen3.5:9b"       # any model installed in your local Ollama instance


# ─────────────────────────────────────────────────────────────────────────────
# 5. TTS  — Chatterbox voice synthesis
# ─────────────────────────────────────────────────────────────────────────────

TTS_REF_AUDIO = "./samples/me.mp3"   # reference voice clip (short, clear speech)

# Voice characteristics
TTS_EXAGGERATION      = 0.6
TTS_TEMPERATURE       = 0.05
TTS_CFG_WEIGHT        = 0.5
TTS_REPETITION_PENALTY = 1.2


# ─────────────────────────────────────────────────────────────────────────────
# 6. MERGE  — how TTS audio is mixed with the original video audio
# ─────────────────────────────────────────────────────────────────────────────

MERGE_MIX_AUDIO = False         # True  = mix TTS + original audio together
                                # False = replace original audio with TTS only

ORIGINAL_AUDIO_VOLUME = 0.5    # 0.0 to 1.0 (e.g., 0.1 = 10% volume)
                                # Only used if MERGE_MIX_AUDIO is True.


# ─────────────────────────────────────────────────────────────────────────────
# 7 & 8. SUBTITLES  — burn-in styling
# ─────────────────────────────────────────────────────────────────────────────

SUBTITLE_FONT_NAME      = "Helvetica"
SUBTITLE_FONT_SIZE      = 20
SUBTITLE_FONT_COLOR     = "#FFFFFF"
SUBTITLE_HIGHLIGHT_COLOR = "#00FFAA"
SUBTITLE_OUTLINE_COLOR   = "#000000"
SUBTITLE_OUTLINE_WIDTH   = 2
SUBTITLE_MAX_WORDS      = 1
SUBTITLE_BOLD           = True
SUBTITLE_ITALIC         = False


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON INTERPRETERS  — one per virtual environment
# Only change if your conda / venv paths differ from the defaults.
# ─────────────────────────────────────────────────────────────────────────────


CHATTERBOX_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "chatterbox", "bin", "python")

FASTER_WHISPER_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "faster_whisper", "bin", "python")
