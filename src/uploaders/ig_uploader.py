#!/usr/bin/env python3
"""
ig_uploader.py
──────────────
Standalone Instagram uploader service.

Usage:
    python ig_uploader.py <video_folder>

Checks for ig_id.txt - only uploads if missing.
"""

import os
import sys

from src import config
from src.upload_config import INSTAGRAM_VIDEO
from src.uploaders.ig_worker import upload_reel

PROJECT_ROOT = config.PROJECT_ROOT


def get_video_path(folder: str) -> str:
    """Get the path to the configured video version."""
    if INSTAGRAM_VIDEO == "mixed":
        return os.path.join(folder, "final_video_mixed.mp4")
    elif INSTAGRAM_VIDEO == "simple":
        return os.path.join(folder, "final_video_simple.mp4")
    else:
        raise ValueError(f"Unknown video version: {INSTAGRAM_VIDEO}")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python ig_uploader.py <video_folder>")
        return 1

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        return 1

    if INSTAGRAM_VIDEO in ("none", "", None):
        print("ℹ️  Instagram upload disabled in config")
        return 0

    video_path = get_video_path(folder)
    if not os.path.exists(video_path):
        print(f"❌ Instagram video not found: {video_path}")
        return 1

    if os.path.exists(os.path.join(folder, "ig_id.txt")):
        print("⚠️  Already uploaded to Instagram (ig_id.txt exists)")
        return 0

    script = os.path.join(folder, "script.txt")
    if not os.path.exists(script):
        print("❌ script.txt missing")
        return 1

    with open(script, "r", encoding="utf-8") as f:
        caption = f.read().strip()

    print(f"🎬 Instagram Uploader (version: {INSTAGRAM_VIDEO})")

    try:
        video_id = upload_reel(video_path, caption)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    id_file = os.path.join(folder, "ig_id.txt")
    with open(id_file, "w") as f:
        f.write(video_id)
    print(f"✅ Instagram upload complete → {video_id}")
    print(f"📝 ID saved → {id_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
