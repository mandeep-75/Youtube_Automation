"""
merge_audio_video.py
--------------------
Merges a TTS-generated audio file (WAV/MP3) with the original silent video,
producing a new MP4 that has the voice-over as its audio track.

The output duration matches the *video* length:
  - If the audio is shorter than the video, it is padded with silence.
  - If the audio is longer than the video, it is trimmed.

This module runs inside the `venvs/faster_whisper` venv (has ffmpeg-python
+ imageio_ffmpeg bundled), so no extra venv is needed.

Usage (standalone):
    python src/merge_audio_video.py \
        --video  h.mp4 \
        --audio  outputs/voice.wav \
        --output outputs/video_with_tts.mp4

Usage (imported):
    from src.merge_audio_video import merge_audio_video
    merge_audio_video("h.mp4", "outputs/voice.wav", "outputs/video_with_tts.mp4")
"""

import argparse
import os
import shutil
import subprocess
import tempfile

# ── resolve bundled ffmpeg ─────────────────────────────────────────────────
# Prioritize local ffmpeg in tools/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_FFMPEG = os.path.join(_ROOT, "tools", "ffmpeg")

if os.path.isfile(_LOCAL_FFMPEG):
    FFMPEG_BIN = _LOCAL_FFMPEG
else:
    try:
        import imageio_ffmpeg
        FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

def _video_duration(path: str) -> float:
    """Return duration in seconds using ffprobe."""
    ffprobe = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or "ffprobe"
    result = subprocess.run(
        [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            path,
        ],
        capture_output=True, text=True, timeout=15,
    )
    return float(result.stdout.strip())


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run an ffmpeg command, raise on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(
            f"[merge] ffmpeg failed (exit {result.returncode}):\n{result.stderr}"
        )


# ══════════════════════════════════════════════════════════════════════════
# Main function
# ══════════════════════════════════════════════════════════════════════════

def merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    *,
    replace_original_audio: bool = True,
) -> str:
    """
    Merge `audio_path` (TTS WAV/MP3) onto `video_path` and write `output_path`.

    Args:
        video_path:              Input video (may be silent or have original audio).
        audio_path:              TTS audio file (WAV, MP3, etc.).
        output_path:             Output MP4 path.
        replace_original_audio:  If True (default), the original video audio (if any)
                                  is discarded and replaced by the TTS audio.
                                  If False, they are mixed together.

    Returns:
        output_path
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    vid_dur = _video_duration(video_path)
    aud_dur = _video_duration(audio_path)

    print(f"[merge] video duration : {vid_dur:.2f}s")
    print(f"[merge] audio duration : {aud_dur:.2f}s")

    tmp_dir = tempfile.mkdtemp(prefix="merge_av_")
    try:
        # ── Step A: normalise the audio to exactly vid_dur seconds ──────────
        # If audio < video → pad with silence
        # If audio > video → trim to video length
        normalised_audio = os.path.join(tmp_dir, "norm_audio.wav")

        if aud_dur < vid_dur:
            pad_secs = vid_dur - aud_dur
            print(f"[merge] Padding audio with {pad_secs:.2f}s of silence ...")
            # adelay / apad approach: concat original + silent tail
            _run_ffmpeg([
                FFMPEG_BIN, "-y",
                "-i", audio_path,
                "-af", f"apad=pad_dur={pad_secs}",
                "-t", str(vid_dur),
                normalised_audio,
            ])
        else:
            print("[merge] Trimming audio to video length ...")
            _run_ffmpeg([
                FFMPEG_BIN, "-y",
                "-i", audio_path,
                "-t", str(vid_dur),
                normalised_audio,
            ])

        # ── Step B: mux video stream + normalised audio ──────────────────────
        print(f"[merge] Muxing video + audio → {output_path} ...")

        if replace_original_audio:
            # -map 0:v  → keep video track from input 0 (video file)
            # -map 1:a  → keep audio track from input 1 (normalised TTS)
            cmd = [
                FFMPEG_BIN, "-y",
                "-i", video_path,
                "-i", normalised_audio,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",          # no re-encode of video
                "-c:a", "aac",
                "-shortest",
                output_path,
            ]
        else:
            # Mix original audio (if present) with TTS using amix
            cmd = [
                FFMPEG_BIN, "-y",
                "-i", video_path,
                "-i", normalised_audio,
                "-filter_complex",
                "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                output_path,
            ]
        _run_ffmpeg(cmd)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    out_dur = _video_duration(output_path)
    print(f"[merge] ✅  Done → {output_path}  ({out_dur:.2f}s)")
    return output_path


# ══════════════════════════════════════════════════════════════════════════
# CLI entry-point
# ══════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge a TTS audio file with the original video."
    )
    parser.add_argument("--video",   required=True, help="Input video file")
    parser.add_argument("--audio",   required=True, help="TTS audio file (WAV/MP3)")
    parser.add_argument("--output",  required=True, help="Output MP4 path")
    parser.add_argument(
        "--mix", action="store_true",
        help="Mix TTS with original audio instead of replacing it",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    merge_audio_video(
        video_path=args.video,
        audio_path=args.audio,
        output_path=args.output,
        replace_original_audio=not args.mix,
    )
