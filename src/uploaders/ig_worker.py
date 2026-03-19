#!/usr/bin/env python3
"""
ig_worker.py
─────────────
Instagram uploader using instagrapi - a simple unofficial API.

Requirements:
    pip install instagrapi

Setup:
    1. Set IG_USERNAME and IG_PASSWORD in .env
    2. Or use session-based auth: ig_session.json will be created after first login
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional

from src import config

PROJECT_ROOT = config.PROJECT_ROOT
SESSION_FILE = os.path.join(PROJECT_ROOT, "ig_session.json")

FFMPEG_PATH = os.path.join(PROJECT_ROOT, "tools", "ffmpeg")
if os.path.isfile(FFMPEG_PATH) and os.access(FFMPEG_PATH, os.X_OK):
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH

# ─────────────────────────────────────────────────────────────────────────────
# SESSION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def get_client():
    """Get or create instagrapi client with session persistence."""
    from instagrapi import Client

    cl = Client()

    if os.path.exists(SESSION_FILE):
        print("   Loading session from ig_session.json...")
        try:
            cl.load_settings(Path(SESSION_FILE))
            cl.get_timeline_feed()
            print("   ✅ Session loaded successfully")
            return cl
        except Exception as e:
            print(f"   ⚠️ Session invalid ({e}), re-authenticating...")

    username = config.IG_USERNAME
    password = config.IG_PASSWORD

    if not username or not password:
        raise ValueError("IG_USERNAME and IG_PASSWORD must be set in .env")

    print(f"   Logging in as @{username}...")
    cl.login(username, password)

    cl.dump_settings(Path(SESSION_FILE))
    print(f"   ✅ Logged in, session saved to {SESSION_FILE}")

    return cl

# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def upload_reel(video_path: str, caption: str) -> str:
    """Upload a Reel to Instagram using instagrapi."""
    cl = get_client()

    print(f"   Uploading: {os.path.basename(video_path)}")
    media = cl.clip_upload(
        path=Path(video_path),
        caption=caption,
    )

    print(f"   ✅ Uploaded! Media ID: {media.id}")
    return str(media.id)


def upload_photo(image_path: str, caption: str) -> str:
    """Upload a photo to Instagram."""
    cl = get_client()

    print(f"   Uploading: {os.path.basename(image_path)}")
    media = cl.photo_upload(
        path=Path(image_path),
        caption=caption,
    )

    print(f"   ✅ Uploaded! Media ID: {media.id}")
    return str(media.id)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python ig_worker.py <video_folder>")
        return 1

    folder = sys.argv[1]
    video = os.path.join(folder, "final_video.mp4")
    script = os.path.join(folder, "script.txt")

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
        print("⚠️  Already uploaded (ig_id.txt exists). Skipping.")
        return 0

    with open(script, "r", encoding="utf-8") as f:
        caption = f.read().strip()

    try:
        print("\n🚀 Uploading Reel to Instagram (instagrapi)...")
        media_id = upload_reel(video, caption)

        id_file = os.path.join(folder, "ig_id.txt")
        with open(id_file, "w") as f:
            f.write(media_id)

        print(f"\n✅ SUCCESS! Reel uploaded")
        print(f"   Media ID: {media_id}")
        return 0
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
