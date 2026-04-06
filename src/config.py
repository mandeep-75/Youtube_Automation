# config.py
# ─────────────────────────────────────────────────────────────────────────────
# ⚙️  PIPELINE SETTINGS
# Edit this file to customise every aspect of the pipeline.
# pipeline.py imports everything from here — you never need to touch it.
# ─────────────────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env after PROJECT_ROOT is defined
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

VISION_MODEL = (
    "qwen3.5:0.8b"  # Model name in Ollama (fast VL model with vision support)
)
VISION_CONTEXT_WINDOW = 5  # Number of previous frames to include as context
VISION_HALLUCINATION_CHECK = False  # Enable hallucination detection in step 2

VISION_PROMPT = """Describe this image in 200 words . Only describe what you actually see. No speculation.Focus on main subject and his work."""


# ─────────────────────────────────────────────────────────────────────────────
# 3. WHISPER  — used in Step 3 (original audio) and Step 7 (TTS subtitles)
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
# 5. TTS  — Chatterbox voice synthesis
# ─────────────────────────────────────────────────────────────────────────────

TTS_REF_AUDIO = "./samples/me2.mp3"  # Primary reference voice clip

# Voice characteristics
TTS_EXAGGERATION = 0.6
TTS_TEMPERATURE = 0.05
TTS_CFG_WEIGHT = 0.5
TTS_REPETITION_PENALTY = 1.2


# ─────────────────────────────────────────────────────────────────────────────
# 6. MERGE  — video version audio settings (legacy, see section 9)
# ─────────────────────────────────────────────────────────────────────────────

ORIGINAL_AUDIO_VOLUME = 0.3  # 0.0 to 1.0 (e.g., 0.1 = 10% volume)
# Volume level for original audio in mixed version


# ─────────────────────────────────────────────────────────────────────────────
# 7 & 8. SUBTITLES  — burn-in styling
# ─────────────────────────────────────────────────────────────────────────────

# CUSTOM SHORTS FONTS (Local TTF files in fonts/ directory):
# Anton natively renders smaller than other fonts, so we give it a larger size to match visually.
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
# PYTHON INTERPRETERS  — one per virtual environment
# Only change if your conda / venv paths differ from the defaults.
# ─────────────────────────────────────────────────────────────────────────────


UNIFIED_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")

CHATTERBOX_PYTHON = UNIFIED_PYTHON
FASTER_WHISPER_PYTHON = UNIFIED_PYTHON
UPLOADER_PYTHON = UNIFIED_PYTHON


# ─────────────────────────────────────────────────────────────────────────────
# 9. UPLOADER SETTINGS
# Note: Upload routing config moved to upload_config.py
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
