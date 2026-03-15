#!/usr/bin/env python3
"""
auto_uploader.py
────────────────
Unified uploader that routes video versions to appropriate platforms
based on config settings (INSTAGRAM_VIDEO and YOUTUBE_VIDEO).

Usage:
    python auto_uploader.py <video_folder>

The folder must contain:
    final_video_mixed.mp4   – video with mixed (original + TTS) audio
    final_video_simple.mp4  – video with TTS-only audio
    script.txt              – narration script (for metadata generation)
"""

import os
import sys

from src import config
from src import upload_config
from src.uploaders.yt_worker import (
    get_authenticated_service as get_youtube_service,
    upload_video as upload_to_youtube,
    generate_metadata,
)
from src.uploaders.ig_worker import (
    upload_reel as upload_to_instagram,
)

PROJECT_ROOT = config.PROJECT_ROOT


def get_video_path(folder: str, version: str) -> str:
    """Get the path to the requested video version."""
    if version == "mixed":
        return os.path.join(folder, "final_video_mixed.mp4")
    elif version == "simple":
        return os.path.join(folder, "final_video_simple.mp4")
    else:
        raise ValueError(f"Unknown video version: {version}")


def upload_to_youtube_wrapper(folder: str, video_path: str) -> bool:
    """Upload video to YouTube. Returns True if successful."""
    script = os.path.join(folder, "script.txt")
    if not os.path.exists(script):
        print("❌ script.txt missing")
        return False

    with open(script, "r", encoding="utf-8") as f:
        script_text = f.read()

    if os.path.exists(os.path.join(folder, "youtube_id.txt")):
        print("⚠️  Already uploaded to YouTube")
        return True

    print("\n🔑 Authenticating with YouTube...")
    try:
        youtube = get_youtube_service()
    except Exception as e:
        print(f"❌ YouTube authentication failed: {e}")
        return False

    try:
        metadata = generate_metadata(script_text)
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        return False

    print(f"\n📋 Title: {metadata.get('title', '?')}")

    try:
        video_id = upload_to_youtube(youtube, video_path, metadata)
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        return False

    id_file = os.path.join(folder, "youtube_id.txt")
    with open(id_file, "w") as f:
        f.write(video_id)
    print(f"📝 YouTube video ID saved → {id_file}")
    return True


def upload_to_instagram_wrapper(folder: str, video_path: str) -> bool:
    """Upload video to Instagram. Returns True if successful."""
    if os.path.exists(os.path.join(folder, "ig_id.txt")):
        print("⚠️  Already uploaded to Instagram")
        return True

    script_path = os.path.join(folder, "script.txt")
    if not os.path.exists(script_path):
        print("❌ script.txt not found for Instagram caption")
        return False

    with open(script_path, "r") as f:
        caption = f.read().strip()

    try:
        video_id = upload_to_instagram(video_path, caption)
    except Exception as e:
        print(f"❌ Instagram upload failed: {e}")
        return False

    id_file = os.path.join(folder, "ig_id.txt")
    with open(id_file, "w") as f:
        f.write(video_id)
    print(f"📝 Instagram video ID saved → {id_file}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python auto_uploader.py <video_folder>")
        return 1

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        return 1

    youtube_video = upload_config.YOUTUBE_VIDEO
    instagram_video = upload_config.INSTAGRAM_VIDEO

    print("\n🎬 Auto-Uploader")
    print(f"   YouTube version:   {youtube_video}")
    print(f"   Instagram version: {instagram_video}")

    yt_success = True
    ig_success = True

    if youtube_video and youtube_video not in ("none", ""):
        video_path = get_video_path(folder, youtube_video)
        if os.path.exists(video_path):
            print(f"\n🚀 Uploading to YouTube ({youtube_video} version)...")
            yt_success = upload_to_youtube_wrapper(folder, video_path)
        else:
            print(f"❌ YouTube video not found: {video_path}")
            yt_success = False

    if instagram_video and instagram_video not in ("none", ""):
        video_path = get_video_path(folder, instagram_video)
        if os.path.exists(video_path):
            print(f"\n🚀 Uploading to Instagram ({instagram_video} version)...")
            ig_success = upload_to_instagram_wrapper(folder, video_path)
        else:
            print(f"❌ Instagram video not found: {video_path}")
            ig_success = False

    if yt_success and ig_success:
        print("\n✅ All uploads completed!")
        return 0
    else:
        print("\n⚠️ Some uploads failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
