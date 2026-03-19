#!/usr/bin/env python3
"""
yt_uploader.py
──────────────
Standalone YouTube uploader service.

Usage:
    python yt_uploader.py <video_folder>

Checks for youtube_id.txt - only uploads if missing.
"""

import os
import sys

from src import config
from src.upload_config import YOUTUBE_VIDEO
from src.uploaders.yt_worker import (
    get_authenticated_service,
    upload_video,
    generate_metadata,
)

PROJECT_ROOT = config.PROJECT_ROOT


def get_video_path(folder: str) -> str:
    """Get the path to the configured video version."""
    if YOUTUBE_VIDEO == "mixed":
        return os.path.join(folder, "final_video_mixed.mp4")
    elif YOUTUBE_VIDEO == "simple":
        return os.path.join(folder, "final_video_simple.mp4")
    else:
        raise ValueError(f"Unknown video version: {YOUTUBE_VIDEO}")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python yt_uploader.py <video_folder>")
        return 1

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        return 1

    if YOUTUBE_VIDEO in ("none", "", None):
        print("ℹ️  YouTube upload disabled in config")
        return 0

    video_path = get_video_path(folder)
    if not os.path.exists(video_path):
        print(f"❌ YouTube video not found: {video_path}")
        return 1

    if os.path.exists(os.path.join(folder, "youtube_id.txt")):
        print("⚠️  Already uploaded to YouTube (youtube_id.txt exists)")
        return 0

    script = os.path.join(folder, "script.txt")
    if not os.path.exists(script):
        print("❌ script.txt missing")
        return 1

    print(f"🎬 YouTube Uploader (version: {YOUTUBE_VIDEO})")

    with open(script, "r", encoding="utf-8") as f:
        script_text = f.read()

    print("\n🔑 Authenticating with YouTube...")
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return 1

    try:
        metadata = generate_metadata(script_text)
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        return 1

    print(f"\n📋 Title: {metadata.get('title', '?')}")

    try:
        video_id = upload_video(youtube, video_path, metadata)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    id_file = os.path.join(folder, "youtube_id.txt")
    with open(id_file, "w") as f:
        f.write(video_id)
    print(f"✅ YouTube upload complete → https://youtu.be/{video_id}")
    print(f"📝 ID saved → {id_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
