#!/usr/bin/env python3
"""
yt_bash_auto_upload.py
──────────────────────
Automated YouTube uploader — no UI, no curses.

Usage (called by autoupload_daily.sh or a bot):
    python yt_bash_auto_upload.py <video_folder>

The folder must contain:
    final_video.mp4   – the video file to upload
    script.txt        – the narration script (used to generate metadata)

On success the script writes youtube_id.txt into the folder and exits 0.
On failure it exits non-zero so the shell script can detect and log it.
"""

import os
import sys
import json
import pickle
import re
import shutil

import ollama

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG  (mirrors config.py so this script is self-contained)
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT        = os.path.dirname(BASE_DIR)

OLLAMA_MODEL        = "jaahas/qwen3.5-uncensored:9b"
SCOPES              = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE  = os.path.join(PROJECT_ROOT, "client_secret.json")
TOKEN_FILE          = os.path.join(PROJECT_ROOT, "youtube_token.pickle")
UPLOADED_DIR        = os.path.join(PROJECT_ROOT, "uploaded")

METADATA_PROMPT = """
You are a YouTube Shorts SEO expert.

Given this video script:

{script}

Create viral metadata.

RULES:
- Title under 90 characters
- Include #shorts
- Description 2 sentences max
- Include 3-5 hashtags
- 10 tags

Return JSON only:

{{
  "title": "...",
  "description": "...",
  "tags": ["tag1","tag2"]
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
        # Try patching unbalanced braces
        if content.count("{") > content.count("}"):
            content += "}" * (content.count("{") - content.count("}"))
        return json.loads(content)


def generate_metadata(script_text: str) -> dict:
    prompt = METADATA_PROMPT.format(script=script_text)
    print("\n💡 Generating metadata with Ollama...\n")

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
# YOUTUBE AUTH
# ─────────────────────────────────────────────────────────────────────────────

def get_authenticated_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️  Token refresh failed ({e}). Re-authenticating...")
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def upload_video(youtube, video_file: str, metadata: dict) -> str:
    body = {
        "snippet": {
            "title":       metadata["title"],
            "description": metadata["description"],
            "tags":        metadata["tags"],
            "categoryId":  "22",
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("\nUploading video...\n")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"\n✅ Upload complete  →  https://youtu.be/{video_id}")
    return video_id


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python yt_bash_auto_upload.py <video_folder>")
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
    if os.path.exists(os.path.join(folder, "youtube_id.txt")):
        print(f"⚠️  Already uploaded (youtube_id.txt exists). Skipping.")
        return 0

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

    print(f"\n📋 Title: {metadata.get('title', '?')}")

    # ── Authenticate & upload ──────────────────────────────────────────────
    print("\n🔑 Authenticating with YouTube...")
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return 1

    try:
        video_id = upload_video(youtube, video, metadata)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    # ── Mark as uploaded ───────────────────────────────────────────────────
    id_file = os.path.join(folder, "youtube_id.txt")
    with open(id_file, "w") as f:
        f.write(video_id)
    print(f"📝 Video ID saved → {id_file}")

    # ── Let the calling script (e.g. autoupload_daily.sh) move the folder ──


    return 0


if __name__ == "__main__":
    sys.exit(main())