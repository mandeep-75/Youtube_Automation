"""
transcribe_original.py
----------------------
Step 1c – Transcribe the ORIGINAL input video to plain text.

This gives the LLM the actual spoken dialogue from the video so it can
generate a much richer script than frame descriptions alone.

Output: outputs/transcript.txt  (timestamped, one line per segment)

Usage:
    python src/transcribe_original.py \\
        --video  input.mp4 \\
        --output outputs/transcript.txt \\
        [--model base] \\
        [--language en]
"""

import argparse
import gc
import os
import shutil
import subprocess
import tempfile

from faster_whisper import WhisperModel

# ── ffmpeg ──────────────────────────────────────────────────────────────────
try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

def _has_audio(video_path: str) -> bool:
    ffprobe = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=15,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True


def _extract_audio(video_path: str, wav_path: str) -> None:
    cmd = [
        FFMPEG_BIN, "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", wav_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"[extract_audio] ffmpeg failed:\n{result.stderr}")


def _format_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ══════════════════════════════════════════════════════════════════════════
# Main transcription logic
# ══════════════════════════════════════════════════════════════════════════

def transcribe_to_txt(
    video_path: str,
    output_path: str,
    model_size: str = "base",
    language: str | None = None,
) -> str:
    """
    Transcribe `video_path` and write a plain-text transcript to `output_path`.

    Each line:  [HH:MM:SS]  segment text

    Returns the path to the written transcript.
    """
    if not _has_audio(video_path):
        print("[transcribe_original] ⚠️  No audio stream found – writing empty transcript.")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        open(output_path, "w").close()
        return output_path

    tmp_dir = tempfile.mkdtemp(prefix="orig_audio_")
    wav_path = os.path.join(tmp_dir, "audio.wav")
    try:
        print(f"[transcribe_original] Extracting audio → {wav_path}")
        _extract_audio(video_path, wav_path)

        print(f"[transcribe_original] Loading Whisper '{model_size}' ...")
        model = WhisperModel(model_size, device="auto", compute_type="int8")

        print("[transcribe_original] Transcribing ...")
        segments_iter, info = model.transcribe(
            wav_path,
            language=language,
            beam_size=5,
            word_timestamps=False,   # segment-level is enough for the LLM
        )
        print(f"[transcribe_original] Detected language: {info.language} "
              f"({info.language_probability:.2f})")

        lines = []
        for seg in segments_iter:
            ts = _format_ts(seg.start)
            lines.append(f"[{ts}] {seg.text.strip()}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        print(f"[transcribe_original] ✅ Transcript saved → {output_path} "
              f"({len(lines)} segments)")
        return output_path

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        gc.collect()


# ══════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe original video audio to a plain-text transcript."
    )
    parser.add_argument("--video",    required=True, help="Input video file")
    parser.add_argument("--output",   required=True, help="Output .txt path")
    parser.add_argument("--model",    default="base", help="Whisper model size (tiny/base/small/medium)")
    parser.add_argument("--language", default=None,  help="Language code (auto-detect if omitted)")
    args = parser.parse_args()

    transcribe_to_txt(
        video_path=args.video,
        output_path=args.output,
        model_size=args.model,
        language=args.language,
    )
