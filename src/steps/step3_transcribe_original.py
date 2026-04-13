import argparse
import gc
import os
import shutil
import subprocess
import tempfile
from typing import Optional

from faster_whisper import WhisperModel

# Prefer the bundled tools/ffmpeg binary (project root/tools/ffmpeg)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_FFMPEG = os.path.join(_PROJECT_ROOT, "tools", "ffmpeg")

if os.path.isfile(_LOCAL_FFMPEG) and os.access(_LOCAL_FFMPEG, os.X_OK):
    FFMPEG_BIN = _LOCAL_FFMPEG
else:
    try:
        import imageio_ffmpeg

        FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


def _has_audio(video_path: str) -> bool:
    ffprobe = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True


def _extract_audio(video_path: str, wav_path: str) -> None:
    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i",
        video_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        wav_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"[extract_audio] ffmpeg failed:\n{result.stderr}")


def _format_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def transcribe_to_txt(
    video_path: str,
    output_path: str,
    model_size: str = "base",
    language: Optional[str] = None,
    beam_size: int = 5,
    compute_type: str = "int8",
) -> str:
    if not _has_audio(video_path):
        print(
            "[transcribe_original] ⚠️  No audio stream found – writing empty transcript."
        )
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            pass  # Create empty file
        return output_path

    tmp_dir = tempfile.mkdtemp(prefix="orig_audio_")
    wav_path = os.path.join(tmp_dir, "audio.wav")
    try:
        print(f"[transcribe_original] Extracting audio → {wav_path}")
        _extract_audio(video_path, wav_path)

        print(f"[transcribe_original] Loading Whisper '{model_size}' ...")
        model = WhisperModel(model_size, device="auto", compute_type=compute_type)

        print("[transcribe_original] Transcribing ...")
        segments_iter, info = model.transcribe(
            wav_path,
            language=language,
            beam_size=beam_size,
            word_timestamps=False,
        )
        print(
            f"[transcribe_original] Detected language: {info.language} "
            f"({info.language_probability:.2f})"
        )

        lines = []
        for seg in segments_iter:
            ts = _format_ts(seg.start)
            lines.append(f"[{ts}] {seg.text.strip()}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        print(
            f"[transcribe_original] ✅ Transcript saved → {output_path} ({len(lines)} segments)"
        )
        return output_path

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        del model
        gc.collect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="base")
    parser.add_argument("--language", default=None)
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()

    transcribe_to_txt(
        video_path=args.video,
        output_path=args.output,
        model_size=args.model,
        language=args.language,
        beam_size=args.beam_size,
        compute_type=args.compute_type,
    )
