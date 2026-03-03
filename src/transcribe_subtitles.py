"""
transcribe_subtitles.py
-----------------------
Uses faster-whisper to transcribe a video file (audio track) and then
burns timed, styled subtitles directly onto the video using FFmpeg and pysubs2.

This version implements "one word burning" (one word at a time) as requested
and avoids MoviePy's ImageMagick dependency.

Usage (standalone):
    python src/transcribe_subtitles.py \
        --video   outputs/voice_over.mp4 \
        --output  outputs/final_subtitled.mp4 \
        [--model  base]        \
        [--language en]        \
        [--srt    outputs/subtitles.srt]
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
import pysubs2

# ── constants / style defaults ─────────────────────────────────────────────
DEFAULT_MODEL    = "base"       # tiny | base | small | medium | large-v3
DEFAULT_DEVICE   = "auto"       # "cpu" | "cuda" | "auto"
DEFAULT_COMPUTE  = "int8"       # "int8" | "float16" | "float32"

# ASS Styles
FONT_NAME        = "Arial"      # standard font
FONT_SIZE        = 20           # ASS font size is different from pixels, 20 is decent
PRIMARY_COLOR    = "&H00FFFFFF" # White (BGR)
OUTLINE_COLOR    = "&H00000000" # Black
OUTLINE_WIDTH    = 1.5
SHADOW_WIDTH     = 0
ALIGNMENT        = 2            # Center-Bottom
MARGIN_V         = 40           # Vertical margin

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
# 3. Burn subtitles onto video
# ══════════════════════════════════════════════════════════════════════════

def burn_subtitles(
    video_path: str,
    segments: list[dict],
    output_path: str,
) -> None:
    """
    Burn subtitles using FFmpeg's 'subtitles' filter with an ASS file.
    This provides high quality and avoids MoviePy dependencies.
    """
    if not segments:
        print("[burn] No segments to burn. Copying video.")
        shutil.copy2(video_path, output_path)
        return

    # 1. Create ASS file with pysubs2 for styling
    subs = pysubs2.SSAFile()
    
    # Define style
    style = pysubs2.SSAStyle(
        fontname=FONT_NAME,
        fontsize=FONT_SIZE,
        primarycolor=pysubs2.Color(*[int(c, 16) for c in ["FF", "FF", "FF"]]), # White
        outlinecolor=pysubs2.Color(0, 0, 0),
        backcolor=pysubs2.Color(0, 0, 0),
        bold=True,
        outline=OUTLINE_WIDTH,
        shadow=SHADOW_WIDTH,
        alignment=ALIGNMENT,
        marginv=MARGIN_V
    )
    subs.styles["Default"] = style

    for seg in segments:
        # pysubs2 uses milliseconds
        start = int(seg["start"] * 1000)
        end = int(seg["end"] * 1000)
        # Avoid zero duration
        if end <= start:
            end = start + 100
        
        event = pysubs2.SSAEvent(start=start, end=end, text=seg["text"])
        subs.append(event)

    # Temporary ASS file
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tmp_ass:
        ass_path = tmp_ass.name
    
    subs.save(ass_path)
    print(f"[burn] Generated temporary ASS: {ass_path}")

    # 2. Run FFmpeg to burn
    # We use path escaping for FFmpeg filters
    escaped_ass_path = ass_path.replace("\\", "/").replace(":", "\\:").replace("'", "'\\''")
    
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", video_path,
        "-vf", f"subtitles='{escaped_ass_path}'",
        "-c:a", "copy",          # copy audio
        "-c:v", "libx264",       # re-encode video
        "-preset", "fast",
        "-crf", "23",
        output_path
    ]

    print(f"[burn] Burning subtitles with FFmpeg ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Cleanup
    if os.path.exists(ass_path):
        os.remove(ass_path)

    if result.returncode != 0:
        print(f"[burn] ❌ FFmpeg failed:\n{result.stderr}")
        raise RuntimeError("FFmpeg subtitle burning failed.")
    
    print(f"[burn] ✅ Done → {output_path}")


# ══════════════════════════════════════════════════════════════════════════
# 4. Public helper
# ══════════════════════════════════════════════════════════════════════════

def transcribe_and_burn(
    video_path: str,
    output_path: str,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,
    srt_path: str | None = None,
) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # 1. Transcribe (returns word-level segments)
    segments = transcribe(video_path, model_size=model_size, language=language)

    # 2. Save SRT if requested
    if srt_path:
        os.makedirs(os.path.dirname(srt_path) or ".", exist_ok=True)
        segments_to_srt(segments, srt_path)

    # 3. Burn subtitles
    burn_subtitles(video_path, segments, output_path)
    return output_path


# ══════════════════════════════════════════════════════════════════════════
# 5. CLI entry-point
# ══════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe and burn word-level subtitles.")
    parser.add_argument("--video",    required=True)
    parser.add_argument("--output",   required=True)
    parser.add_argument("--model",    default=DEFAULT_MODEL)
    parser.add_argument("--language", default=None)
    parser.add_argument("--srt",      default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    transcribe_and_burn(
        video_path=args.video,
        output_path=args.output,
        model_size=args.model,
        language=args.language,
        srt_path=args.srt,
    )
