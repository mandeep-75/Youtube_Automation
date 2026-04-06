# config.py
# ─────────────────────────────────────────────────────────────────────────────
# ⚙️  PIPELINE SETTINGS
# Edit this file to customise every aspect of the pipeline.
# pipeline.py imports everything from here — you never need to touch it.
# ─────────────────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ─────────────────────────────────────────────────────────────────────────────
# 0. GLOBAL / COMMON SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"


# ─────────────────────────────────────────────────────────────────────────────
# 1. FRAME EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

FRAME_INTERVAL = "1.0"  # seconds between extracted frames (lower = more frames)


# ─────────────────────────────────────────────────────────────────────────────
# 2. VISION MODEL  — visual frame description (via Ollama)
# ─────────────────────────────────────────────────────────────────────────────

VISION_MODEL = "qwen3.5:0.8b"  # Fast VL model with vision support (873M params)
VISION_CONTEXT_WINDOW = 5  # Number of previous frames to include as context
VISION_HALLUCINATION_CHECK = False  # Enable hallucination detection in step 2

VISION_PROMPT = """Describe this image in 200 words. Only describe what you actually see. No speculation. Focus on main subject and his work."""


# ─────────────────────────────────────────────────────────────────────────────
# 3. WHISPER  — used in Step 3 (original audio) and Step 7 (subtitles)
# ─────────────────────────────────────────────────────────────────────────────

WHISPER_MODEL = "base"  # tiny | base | small | medium | large-v3
WHISPER_LANG = None  # e.g. "en" to force English, or None for auto-detect
WHISPER_BEAM_SIZE = 5
WHISPER_COMPUTE_TYPE = "int8"  # int8 | float16 | float32


# ─────────────────────────────────────────────────────────────────────────────
# 4. LLM SCRIPT  — Ollama model for narration script generation
# ─────────────────────────────────────────────────────────────────────────────

LLM_MODEL = "qwen3.5:9b"
LLM_WORDS_PER_SECOND = 3  # Target words per second for narration


# ─────────────────────────────────────────────────────────────────────────────
# 5. TTS + MUSIC  — ACE-Step 1.5 via ComfyUI
# Script becomes lyrics, ACE-Step generates vocals + background music
# ─────────────────────────────────────────────────────────────────────────────

COMFYUI_URL = "http://127.0.0.1:8000"
COMFYUI_WORKFLOW_PATH = os.path.join(PROJECT_ROOT, "workflows", "ace_step_music.json")

# Music generation defaults
MUSIC_STYLE = "epic cinematic ambient pop"  # Default style
MUSIC_BPM = 120  # Beats per minute
MUSIC_KEYSCALE = "C minor"  # Musical key


# ─────────────────────────────────────────────────────────────────────────────
# 6. MERGE  — video version audio settings
# ─────────────────────────────────────────────────────────────────────────────

ORIGINAL_AUDIO_VOLUME = 0.3  # 0.0 to 1.0 (volume in mixed version)


# ─────────────────────────────────────────────────────────────────────────────
# 7 & 8. SUBTITLES  — burn-in styling
# ─────────────────────────────────────────────────────────────────────────────

# CUSTOM SHORTS FONTS (Local TTF files in fonts/ directory):
SUBTITLE_FONTS = [
    {"name": "Anton", "size": 120},
    {"name": "Bebas Neue", "size": 120},
    {"name": "Oswald", "size": 120},
]
SUBTITLE_FONT_COLOR = "#FFFFFF"
SUBTITLE_HIGHLIGHT_COLOR = "#00FFAA"
SUBTITLE_OUTLINE_COLOR = "#000000"
SUBTITLE_OUTLINE_WIDTH = 1
SUBTITLE_MAX_WORDS = 3
SUBTITLE_BOLD = True
SUBTITLE_ITALIC = False
SUBTITLE_POSITION = "center"  # top, center, bottom
SUBTITLE_X_OFFSET = -50
SUBTITLE_Y_OFFSET = 250


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON INTERPRETERS  — unified venv
# ─────────────────────────────────────────────────────────────────────────────

UNIFIED_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
FASTER_WHISPER_PYTHON = UNIFIED_PYTHON


# ─────────────────────────────────────────────────────────────────────────────
# 9. UPLOADER SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = os.path.join(PROJECT_ROOT, "client_secret.json")
YOUTUBE_TOKEN_FILE = os.path.join(PROJECT_ROOT, "youtube_token.pickle")
IG_SESSION_FILE = os.path.join(PROJECT_ROOT, "ig_session.json")

IG_USERNAME = os.environ.get("IG_USERNAME", "")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")

# Instagram Graph API (Official)
IG_GRAPH_API_VERSION = "v23.0"
IG_GRAPH_ACCESS_TOKEN = os.environ.get("IG_GRAPH_ACCESS_TOKEN", "")
IG_GRAPH_USER_ID = os.environ.get("IG_GRAPH_USER_ID", "")
