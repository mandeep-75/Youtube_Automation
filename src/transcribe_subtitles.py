"""
transcribe_subtitles.py
-----------------------
Uses faster-whisper to transcribe a video file (audio track) and export
word-level timestamps to SRT subtitle format.

Subtitle burning/styling is handled separately by burn_subtitles.py
for better modularity and customization options.

Usage (standalone):
    python src/transcribe_subtitles.py \
        --video   video.mp4 \
        --srt     subtitles.srt \
        [--model  base]        \
        [--language en]

Then burn subtitles with custom styling:
    python src/burn_subtitles.py video.mp4 subtitles.srt -o output.mp4 --font-size 28
"""

import argparse
import os
import sys
import math
import subprocess
import tempfile
import shutil
import gc

# ── third-party (faster_whisper venv) ─────────────────────────────────────
from faster_whisper import WhisperModel

# ── constants ──────────────────────────────────────────────────────────────
DEFAULT_MODEL    = "base"       # tiny | base | small | medium | large-v3
DEFAULT_DEVICE   = "auto"       # "cpu" | "cuda" | "auto"
DEFAULT_COMPUTE  = "int8"       # "int8" | "float16" | "float32"

# Path to ffmpeg
try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


# ══════════════════════════════════════════════════════════════════════════
# 0. Audio helpers
# ══════════════════════════════════════════════════════════════════════════

def has_audio(video_path: str) -> bool:
    ffprobe = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                video_path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True


def extract_audio_wav(video_path: str, wav_path: str) -> None:
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav",
        wav_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"[extract_audio] ffmpeg failed:\n{result.stderr}")


# ══════════════════════════════════════════════════════════════════════════
# 1. Transcription
# ══════════════════════════════════════════════════════════════════════════

def transcribe(
    video_path: str,
    model_size: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE,
    language: str | None = None,
) -> list[dict]:
    """
    Transcribe with word-level timestamps to support 'one word burning'.
    Returns a list of word segments: {"start": float, "end": float, "text": str}
    """
    if not has_audio(video_path):
        print(f"[transcribe] ⚠️ No audio stream found. Returning empty.")
        return []

    tmp_dir = tempfile.mkdtemp(prefix="fw_audio_")
    wav_path = os.path.join(tmp_dir, "audio.wav")
    try:
        print(f"[transcribe] Extracting audio → {wav_path} ...")
        extract_audio_wav(video_path, wav_path)

        print(f"[transcribe] Loading model '{model_size}' ...")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        print(f"[transcribe] Transcribing with word_timestamps=True ...")
        segments_iter, info = model.transcribe(
            wav_path,
            language=language,
            beam_size=5,
            word_timestamps=True,  # CRITICAL for one word burning
        )

        print(f"[transcribe] Language: {info.language} ({info.language_probability:.2f})")

        words = []
        for segment in segments_iter:
            if segment.words:
                for word in segment.words:
                    words.append({
                        "start": word.start,
                        "end": word.end,
                        "text": word.word.strip()
                    })
            else:
                # Fallback if words are missing
                words.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })

        print(f"[transcribe] Total words: {len(words)}")
        return words

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        gc.collect()


# ══════════════════════════════════════════════════════════════════════════
# 2. Export to SRT
# ══════════════════════════════════════════════════════════════════════════

def _seconds_to_srt_time(seconds: float) -> str:
    hours   = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs    = int(seconds % 60)
    millis  = int(round((seconds - math.floor(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: list[dict], srt_path: str) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start_ts = _seconds_to_srt_time(seg["start"])
        end_ts   = _seconds_to_srt_time(seg["end"])
        text     = seg["text"]
        lines.append(f"{i}\n{start_ts} --> {end_ts}\n{text}\n")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[srt] Saved SRT to: {srt_path}")


# ══════════════════════════════════════════════════════════════════════════
# 3. Public helper – transcribe and export SRT
# ══════════════════════════════════════════════════════════════════════════

def transcribe_and_export_srt(
    video_path: str,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,
    srt_path: str | None = None,
) -> str:
    """
    Transcribe a video and optionally export to SRT format.
    
    Note: Subtitle burning is now handled separately by burn_subtitles.py
    for better modularity and customization.
    """
    if srt_path:
        os.makedirs(os.path.dirname(srt_path) or ".", exist_ok=True)

    # Transcribe (returns word-level segments)
    segments = transcribe(video_path, model_size=model_size, language=language)

    # Save SRT if requested
    if srt_path:
        segments_to_srt(segments, srt_path)
        return srt_path
    
    return ""


# ══════════════════════════════════════════════════════════════════════════
# 4. CLI entry-point
# ══════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audio to SRT subtitles using faster-whisper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Note: Subtitle burning is now handled separately by burn_subtitles.py
for better modularity and customization options.

Examples:
  # Transcribe and save SRT
  python transcribe_subtitles.py --video input.mp4 --srt output.srt

  # Then burn subtitles using the dedicated script
  python burn_subtitles.py input.mp4 output.srt -o final.mp4
        """
    )
    parser.add_argument("--video",    required=True, help="Input video file")
    parser.add_argument("--output",   help="Deprecated: use --srt instead")
    parser.add_argument("--model",    default=DEFAULT_MODEL, help="Whisper model size")
    parser.add_argument("--language", default=None, help="Language code (auto-detect if not specified)")
    parser.add_argument("--srt",      default=None, help="Path to save SRT subtitle file")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    
    # Handle deprecated --output flag for backwards compatibility
    srt_path = args.srt or args.output
    
    if not srt_path:
        print("Error: Please specify --srt to save subtitle file")
        sys.exit(1)
    
    transcribe_and_export_srt(
        video_path=args.video,
        model_size=args.model,
        language=args.language,
        srt_path=srt_path,
    )
