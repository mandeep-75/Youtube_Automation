import os

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

VIDEO_INPUT_DIR = os.getenv("VIDEO_INPUT_DIR", "")

OLLAMA_URL = "http://localhost:11434"

DEBUG_MODE = False
DEBUG_MAX_FRAMES = 2

FRAME_INTERVAL = "2.0"

VISION_MODEL = "qwen3.5:0.8b"
VISION_PROMPT = """Describe this image briefly in 2-3 sentences. Only what you see. Focus on main subject and action."""

WHISPER_MODEL = "base"
WHISPER_LANG = None
WHISPER_BEAM_SIZE = 5
WHISPER_COMPUTE_TYPE = "int8"

LLM_MODEL = "qwen3.5:9b"
LLM_WORDS_PER_SECOND = 4

TTS_MODEL = "KittenML/kitten-tts-mini-0.8"
TTS_VOICE = "Hugo"
TTS_SPEED = 1.2

PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1920
PORTRAIT_BG_COLOR = "#000000"

SUBTITLE_FONTS = [
    {"name": "Anton", "size": 150},
    {"name": "Bebas Neue", "size": 150},
    {"name": "Oswald", "size": 150},
]
SUBTITLE_FONT_COLOR = "#FFFFFF"
SUBTITLE_HIGHLIGHT_COLOR = "#00FFAA"
SUBTITLE_OUTLINE_COLOR = "#000000"
SUBTITLE_OUTLINE_WIDTH = 1
SUBTITLE_MAX_WORDS = 3
SUBTITLE_BOLD = True
SUBTITLE_ITALIC = False
SUBTITLE_POSITION = "center"
SUBTITLE_X_OFFSET = -50
SUBTITLE_Y_OFFSET = 250

PIPELINE_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
