import argparse
import os
import sys
import subprocess
import tempfile
import shutil
import gc

from faster_whisper import WhisperModel


DEFAULT_MODEL = "base"
DEFAULT_DEVICE = "auto"
DEFAULT_COMPUTE = "int8"


try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


def get_ffprobe():
    ffprobe = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if os.path.isfile(ffprobe):
        return ffprobe
    return shutil.which("ffprobe") or "ffprobe"


def has_audio(video_path: str) -> bool:

    ffprobe = get_ffprobe()

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                video_path
            ],
            capture_output=True,
            text=True,
            timeout=15
        )

        return bool(result.stdout.strip())

    except Exception:
        return True


def extract_audio_wav(video_path: str, wav_path: str):

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-f", "wav",
        wav_path
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def seconds_to_srt(seconds: float) -> str:

    millis = int(round(seconds * 1000))

    hours = millis // 3600000
    millis %= 3600000

    minutes = millis // 60000
    millis %= 60000

    secs = millis // 1000
    millis %= 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def clean_segments(words):

    cleaned = []
    prev_end = None

    for w in words:

        text = w["text"].strip()

        if not text:
            continue

        start = w["start"]
        end = w["end"]

        # remove hallucinated long words
        if end - start > 2:
            continue

        # remove silence hallucinations
        if prev_end is not None:
            gap = start - prev_end
            if gap > 5:
                continue

        cleaned.append({
            "start": start,
            "end": end,
            "text": text
        })

        prev_end = end

    return cleaned


def transcribe(
    video_path: str,
    model_size: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE,
    language=None,
    beam_size: int = 5
):

    if not has_audio(video_path):
        print("⚠️ No audio stream found.")
        return []

    tmp_dir = tempfile.mkdtemp(prefix="fw_audio_")
    wav_path = os.path.join(tmp_dir, "audio.wav")

    try:

        print("Extracting audio...")
        extract_audio_wav(video_path, wav_path)

        print("Loading model:", model_size)
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

        print("Transcribing...")

        segments_iter, info = model.transcribe(
            wav_path,
            language=language,
            beam_size=beam_size,
            word_timestamps=True
        )

        print("Language:", info.language)

        words = []

        for segment in segments_iter:

            if segment.words:

                for word in segment.words:

                    text = word.word.strip()

                    # remove punctuation only
                    if text in {".", ",", "!", "?"}:
                        continue

                    words.append({
                        "start": word.start,
                        "end": word.end,
                        "text": text
                    })

            else:

                text = segment.text.strip()

                if text:
                    words.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": text
                    })

        print("Words detected:", len(words))

        return words

    finally:

        shutil.rmtree(tmp_dir, ignore_errors=True)
        gc.collect()


def segments_to_srt(segments, srt_path):

    lines = []

    for i, seg in enumerate(segments, start=1):

        start_ts = seconds_to_srt(seg["start"])
        end_ts = seconds_to_srt(seg["end"])

        text = seg["text"]

        lines.append(
            f"{i}\n{start_ts} --> {end_ts}\n{text}\n"
        )

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Saved SRT →", srt_path)


def transcribe_and_export_srt(
    video_path,
    model_size=DEFAULT_MODEL,
    language=None,
    srt_path=None,
    beam_size=5,
    compute_type=DEFAULT_COMPUTE
):

    segments = transcribe(
        video_path,
        model_size=model_size,
        language=language,
        beam_size=beam_size,
        compute_type=compute_type
    )

    segments = clean_segments(segments)

    if srt_path:

        os.makedirs(os.path.dirname(srt_path) or ".", exist_ok=True)

        segments_to_srt(segments, srt_path)

        return srt_path

    return ""


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--video", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--language", default=None)
    parser.add_argument("--srt", required=True)
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--compute-type", default=DEFAULT_COMPUTE)

    args = parser.parse_args()

    transcribe_and_export_srt(
        video_path=args.video,
        model_size=args.model,
        language=args.language,
        srt_path=args.srt,
        beam_size=args.beam_size,
        compute_type=args.compute_type
    )