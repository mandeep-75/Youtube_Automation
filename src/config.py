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

# Debug mode for faster testing
DEBUG_MODE = True # Set to True to enable debug features
DEBUG_MAX_FRAMES = 2  # Maximum frames to extract in step 1 (only when DEBUG_MODE=True)

# Use direct imports instead of subprocess for pipeline steps
# Direct imports are faster but require all steps to be importable
USE_DIRECT_IMPORTS = False  # Set to True for faster execution


# ─────────────────────────────────────────────────────────────────────────────
# 1. FRAME EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

FRAME_INTERVAL = "2.0"  # seconds between extracted frames (lower = more frames)


# ─────────────────────────────────────────────────────────────────────────────
# 2. VISION MODEL  — visual frame description (via Ollama)
# ─────────────────────────────────────────────────────────────────────────────

VISION_MODEL = "qwen3.5:0.8b"  # Fast VL model with vision support (873M params)
VISION_CONTEXT_WINDOW = 5  # Number of previous frames to include as context

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
LLM_WORDS_PER_SECOND = 4  # Target words per second for narration


# ─────────────────────────────────────────────────────────────────────────────
# 5. TTS + MUSIC  — Choose between ACE-Step music or Chatterbox TTS
# ─────────────────────────────────────────────────────────────────────────────

# Audio generation mode:
# - True: Use ACE-Step 1.5 via ComfyUI (vocals + background music)
# - False: Use MLX Qwen3-TTS (voice only, no music)
USE_ACE_MUSIC = False  # Default: use MLX Qwen3-TTS

# ==== ACE-Step 1.5 Settings (when USE_ACE_MUSIC = True) ====

COMFYUI_URL = "http://127.0.0.1:8000"
COMFYUI_WORKFLOW_PATH = os.path.join(PROJECT_ROOT, "workflows", "ace_step_music.json")

# Music generation defaults
MUSIC_STYLE = """A smooth but energetic modern ambient-pop / rap track with a pleasant and uplifting atmosphere.
Driven by warm ambient synth pads, a deep pulsing bassline, and crisp electronic drums instead of distorted guitars.
The vocals are clear and prominent, featuring a female lead who alternates between melodic singing and rhythmic rap
verses. The rap delivery is confident and smooth, sitting tightly with the beat while the sung sections feel airy
and emotional. The track gradually builds from a calm, atmospheric intro into a brighter and more powerful chorus,
blending lo-fi textures, atmospheric sound design, and modern hip-hop rhythms to create a relaxed but engaging
listening experience."""
MUSIC_BPM = 120
MUSIC_KEYSCALE = "C minor"

# ComfyUI output directory where generated audio files are saved
COMFYUI_OUTPUT_DIR = os.environ.get(
    "COMFYUI_OUTPUT_DIR", "/Users/mandeep/Downloads/comfy/output"
)

# ==== Qwen3-TTS Settings (when USE_ACE_MUSIC = False) ====
# DEPRECATED: Using Piper TTS instead (see below)

# ==== MLX Qwen3-TTS Settings ====
# Apple Silicon optimized TTS with voice cloning
# Model: mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit
MLX_TTS_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
MLX_TTS_REF_AUDIO = os.path.join(PROJECT_ROOT, "samples", "me.mp3")
MLX_TTS_SAMPLE_RATE = 24000  # Default output sample rate


# ─────────────────────────────────────────────────────────────────────────────
# 6. MERGE  — video version audio settings
# ─────────────────────────────────────────────────────────────────────────────

# If True, mix generated audio with original video audio
# If False, replace original audio entirely
MERGE_MIX_AUDIO = False  # Default to False for clean output

ORIGINAL_AUDIO_VOLUME = 0.3  # 0.0 to 1.0 (volume when mixing)


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
# PYTHON INTERPRETER  — unified venv
# ─────────────────────────────────────────────────────────────────────────────

PIPELINE_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")


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
