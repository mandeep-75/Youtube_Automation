# upload_config.py
# ─────────────────────────────────────────────────────────────────────────────
# 📤 UPLOAD CONFIGURATION
# Edit this file to control which video version goes to each platform.
# ─────────────────────────────────────────────────────────────────────────────

# Video version options: "mixed" (original + TTS) or "simple" (TTS only)
# "mixed" - original audio + TTS (may have copyright issues on YouTube)
# "simple" - TTS only, original audio replaced (safer for YouTube)

INSTAGRAM_VIDEO = "none"   # Disabled - set to "mixed" or "simple" to enable
YOUTUBE_VIDEO = "simple"   # Which version to upload to YouTube

# Set to "" or "none" to disable upload to that platform
# Example: YOUTUBE_VIDEO = "none" to skip YouTube uploads
