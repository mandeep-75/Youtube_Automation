import argparse
import os
import shutil
import subprocess
import tempfile

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


def _video_duration(path: str) -> float:
    ffprobe = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or "ffprobe"
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=15,
    )
    return float(result.stdout.strip())


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(
            f"[merge] ffmpeg failed (exit {result.returncode}):\n{result.stderr}"
        )


def merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    *,
    replace_original_audio: bool = True,
) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    vid_dur = _video_duration(video_path)
    aud_dur = _video_duration(audio_path)

    print(f"[merge] video duration : {vid_dur:.2f}s")
    print(f"[merge] audio duration : {aud_dur:.2f}s")

    tmp_dir = tempfile.mkdtemp(prefix="merge_av_")
    try:
        normalised_audio = os.path.join(tmp_dir, "norm_audio.wav")

        if aud_dur < vid_dur:
            pad_secs = vid_dur - aud_dur
            print(f"[merge] Padding audio with {pad_secs:.2f}s of silence ...")
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

        print(f"[merge] Muxing video + audio → {output_path} ...")

        if replace_original_audio:
            cmd = [
                FFMPEG_BIN, "-y",
                "-i", video_path,
                "-i", normalised_audio,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path,
            ]
        else:
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",  required=True)
    parser.add_argument("--audio",  required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mix", action="store_true")
    args = parser.parse_args()

    merge_audio_video(
        video_path=args.video,
        audio_path=args.audio,
        output_path=args.output,
        replace_original_audio=not args.mix,
    )
