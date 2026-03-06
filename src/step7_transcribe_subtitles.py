import argparse
import os
import sys
import math
import subprocess
import tempfile
import shutil
import gc

from faster_whisper import WhisperModel

DEFAULT_MODEL   = "base"
DEFAULT_DEVICE  = "auto"
DEFAULT_COMPUTE = "int8"

try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


def has_audio(video_path: str) -> bool:
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


def transcribe(
    video_path: str,
    model_size: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE,
    language: str | None = None,
    beam_size: int = 5,
) -> list[dict]:
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
            beam_size=beam_size,
            word_timestamps=True,
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


def transcribe_and_export_srt(
    video_path: str,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,
    srt_path: str | None = None,
    beam_size: int = 5,
    compute_type: str = DEFAULT_COMPUTE,
) -> str:
    if srt_path:
        os.makedirs(os.path.dirname(srt_path) or ".", exist_ok=True)

    segments = transcribe(video_path, model_size=model_size, language=language, beam_size=beam_size, compute_type=compute_type)

    if srt_path:
        segments_to_srt(segments, srt_path)
        return srt_path

    return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",        required=True)
    parser.add_argument("--output",       help="Deprecated: use --srt instead")
    parser.add_argument("--model",        default=DEFAULT_MODEL)
    parser.add_argument("--language",     default=None)
    parser.add_argument("--srt",          default=None)
    parser.add_argument("--beam-size",    type=int, default=5)
    parser.add_argument("--compute-type", default=DEFAULT_COMPUTE)
    args = parser.parse_args()

    srt_path = args.srt or args.output

    if not srt_path:
        print("Error: Please specify --srt to save subtitle file")
        sys.exit(1)

    transcribe_and_export_srt(
        video_path=args.video,
        model_size=args.model,
        language=args.language,
        srt_path=srt_path,
        beam_size=args.beam_size,
        compute_type=args.compute_type,
    )
