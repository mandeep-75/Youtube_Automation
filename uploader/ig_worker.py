#!/usr/bin/env python3
"""
ig_bash_auto_upload.py
──────────────────────
Automated Instagram Reels uploader — no UI.

Usage (called by a bash script or a bot):
    python ig_bash_auto_upload.py <video_folder>

The folder must contain:
    final_video.mp4   – the video file to upload
    script.txt        – the narration script (used to generate caption)

Environment variables required (or set via .env / inline):
    IG_USERNAME
    IG_PASSWORD

On success the script writes ig_id.txt into the folder and exits 0.
On failure it exits non-zero so the shell script can detect and log it.
"""

import os
import sys
import json
import re
from pathlib import Path

import ollama
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from dotenv import load_dotenv

BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT        = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

OLLAMA_MODEL        = "jaahas/qwen3.5-uncensored:9b"
IG_SESSION_FILE     = os.path.join(PROJECT_ROOT, "ig_session.json")

# Load credentials from environment (or set them here directly)
IG_USERNAME = os.environ.get("IG_USERNAME", "")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")

METADATA_PROMPT = """
You are an Instagram Reels viral SEO expert.

Given this video script:

{script}

Create an engaging Instagram Reels caption.

RULES:
- Start with a catchy hook line
- Short engaging description (1-2 sentences)
- Include 5 to 10 relevant hashtags at the end
- Use a few emojis
- Do NOT include any markdown or text outside the JSON.

Return JSON only:

{{
  "caption": "Your generated caption here with #hashtags"
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in LLM response")
    content = match.group(1)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        if content.count("{") > content.count("}"):
            content += "}" * (content.count("{") - content.count("}"))
        return json.loads(content)

def generate_metadata(script_text: str) -> dict:
    prompt = METADATA_PROMPT.format(script=script_text)
    print("\n💡 Generating Instagram caption with Ollama...\n")

    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": 0.8},
    )

    response_text = ""
    for chunk in stream:
        content = getattr(chunk.message, "content", None)
        if content:
            print(content, end="", flush=True)
            response_text += content

    print("\n")
    return extract_json(response_text)

# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM AUTH
# ─────────────────────────────────────────────────────────────────────────────

def get_authenticated_client():
    cl = Client()
    
    # Try loading an existing session first
    if os.path.exists(IG_SESSION_FILE):
        cl.load_settings(IG_SESSION_FILE)
        try:
            # Login required to ensure the loaded session is valid and active
            cl.login(IG_USERNAME, IG_PASSWORD)
            return cl
        except Exception as e:
            print(f"⚠️  Session expired or login failed ({e}). Re-authenticating...")
    
    if not IG_USERNAME or not IG_PASSWORD:
        raise ValueError("IG_USERNAME and IG_PASSWORD must be set in the script or environment.")
        
    # Performs a completely fresh login
    print("🔑 Logging into Instagram...")
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.dump_settings(IG_SESSION_FILE)
    return cl

# ─────────────────────────────────────────────────────────────────────────────
# VIDEO UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def upload_video(cl, video_file: str, metadata: dict) -> str:
    caption = metadata.get("caption", "Default caption")
    print(f"\nUploading Reel to Instagram...\nCaption: {caption}\n")
    
    # clip_upload supports instagram reels.
    media = cl.clip_upload(path=video_file, caption=caption)
    video_pk = media.pk
    video_code = media.code
    
    print(f"\n✅ Upload complete  →  https://www.instagram.com/reel/{video_code}/")
    return str(video_pk)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python ig_bash_auto_upload.py <video_folder>")
        return 1

    folder = sys.argv[1]
    video  = os.path.join(folder, "final_video.mp4")
    script = os.path.join(folder, "script.txt")

    # ── Validate inputs ────────────────────────────────────────────────────
    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        return 1
    if not os.path.exists(video):
        print(f"❌ final_video.mp4 missing in {folder}")
        return 1
    if not os.path.exists(script):
        print(f"❌ script.txt missing in {folder}")
        return 1
    if os.path.exists(os.path.join(folder, "ig_id.txt")):
        print(f"⚠️  Already uploaded (ig_id.txt exists). Skipping.")
        return 0

    if not IG_USERNAME or not IG_PASSWORD:
        print("❌ Error: IG_USERNAME and IG_PASSWORD environment variables are not set.")
        print("   Set them via Export, or edit this script directly.")
        return 1

    # ── Read script ────────────────────────────────────────────────────────
    print(f"\n📄 Reading script from {script}")
    with open(script, "r", encoding="utf-8") as f:
        script_text = f.read()

    # ── Generate metadata ──────────────────────────────────────────────────
    try:
        metadata = generate_metadata(script_text)
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        return 1

    # ── Authenticate & upload ──────────────────────────────────────────────
    print("\n🔑 Authenticating with Instagram...")
    try:
        client = get_authenticated_client()
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return 1

    try:
        video_id = upload_video(client, video, metadata)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    # ── Mark as uploaded ───────────────────────────────────────────────────
    id_file = os.path.join(folder, "ig_id.txt")
    with open(id_file, "w") as f:
        f.write(video_id)
    print(f"📝 Instagram PK saved → {id_file}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
