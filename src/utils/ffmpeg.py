# utils/ffmpeg.py
# ─────────────────────────────────────────────────────────────────────────────
# FFmpeg/FFprobe utility functions
# Centralizes FFmpeg detection to reduce duplication across pipeline steps
# ─────────────────────────────────────────────────────────────────────────────

import os
import shutil
from typing import Optional, Tuple

# Project root for local ffmpeg binary
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_ffmpeg_bin() -> str:
    """
    Get the path to ffmpeg binary.

    Priority:
    1. Local tools/ffmpeg in project root
    2. imageio-ffmpeg bundled binary
    3. System ffmpeg in PATH

    Returns:
        Path to ffmpeg executable
    """
    # 1. Check local tools/ffmpeg
    local_ffmpeg = os.path.join(_PROJECT_ROOT, "tools", "ffmpeg")
    if os.path.isfile(local_ffmpeg):
        return local_ffmpeg

    # 2. Try imageio-ffmpeg (bundled)
    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.isfile(bundled):
            return bundled
    except ImportError:
        pass

    # 3. Fall back to system ffmpeg
    system_ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    return system_ffmpeg


def get_ffprobe_bin() -> str:
    """
    Get the path to ffprobe binary.

    Returns:
        Path to ffprobe executable
    """
    ffmpeg = get_ffmpeg_bin()

    # Try local ffprobe first
    ffprobe_local = ffmpeg.replace("ffmpeg", "ffprobe")
    if os.path.isfile(ffprobe_local):
        return ffprobe_local

    # Try system ffprobe
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    return ffprobe


def get_video_duration(video_path: str) -> Optional[float]:
    """
    Get video duration in seconds using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds, or None if unable to determine
    """
    ffprobe = get_ffprobe_bin()

    try:
        import subprocess

        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def get_video_resolution(video_path: str) -> Optional[Tuple[int, int]]:
    """
    Get video resolution (width, height) using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Tuple of (width, height), or None if unable to determine
    """
    ffprobe = get_ffprobe_bin()

    try:
        import subprocess

        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=s=,:p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        width, height = map(int, result.stdout.strip().split(","))
        return (width, height)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None
