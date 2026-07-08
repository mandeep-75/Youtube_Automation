"""
YouTube Automation Pipeline
===========================
Processes raw videos into narrated, subtitled YouTube Shorts.

Usage:
    python pipeline.py video.mp4
    python pipeline.py --debug video.mp4
    python pipeline.py --script-ref reference_script.txt video.mp4
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src import config


def get_video_duration(video_path: str) -> float:
    ffprobe = os.path.join(config.PROJECT_ROOT, "tools", "ffprobe")
    if not (os.path.isfile(ffprobe) and os.access(ffprobe, os.X_OK)):
        ffprobe = "ffprobe"
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError(f"Invalid duration {duration} for video: {video_path}")
    return duration


def resolve_video_path(video_path: str) -> str:
    if not os.path.isabs(video_path) and config.VIDEO_INPUT_DIR:
        resolved = os.path.join(config.VIDEO_INPUT_DIR, video_path)
        if os.path.isfile(resolved):
            return resolved
    return video_path


def run_pipeline(video_path: str, script_ref: str | None = None) -> None:
    video_path = resolve_video_path(video_path)
    video_name = os.path.splitext(re.sub(r'[<>:"/\\|?*]', "_", os.path.basename(video_path)).strip(". ") or "unnamed_video")[0]
    out = os.path.join(config.PROJECT_ROOT, "yt_inbox", video_name)
    os.makedirs(out, exist_ok=True)

    frames_dir = os.path.join(out, "frames")
    frames_file = os.path.join(out, "frames.txt")
    transcript_file = os.path.join(out, "transcript.txt")
    script_file = os.path.join(out, "script.txt")
    voice_file = os.path.join(out, "voice.wav")
    final_video = os.path.join(out, f"{video_name}.mp4")

    py = config.PIPELINE_PYTHON
    steps = os.path.join(config.PROJECT_ROOT, "src", "steps")

    print(f"\n🚀 Processing: {video_path}")
    print(f"📂 Output: {out}")

    print("\n─── Step 1  Analyze (extract + describe frames) ─────────")
    subprocess.run([
        py, os.path.join(steps, "step1_analyze.py"),
        "--video-file", video_path,
        "--interval", config.FRAME_INTERVAL,
        "--output-dir", frames_dir,
        "--frames-file", frames_file,
    ], check=True)

    print("\n─── Step 2  Script (transcribe + generate script) ───────")
    duration = get_video_duration(video_path)
    cmd = [
        py, os.path.join(steps, "step2_script.py"),
        "--video", video_path,
        "--frames-file", frames_file,
        "--transcript-file", transcript_file,
        "--script-file", script_file,
        "--duration", f"{duration:.2f}",
    ]
    if script_ref:
        cmd.extend(["--script-ref", script_ref])
    subprocess.run(cmd, check=True)

    print("\n─── Step 3  TTS audio ───────────────────────────────────")
    subprocess.run([
        py, os.path.join(steps, "step3_tts.py"),
        "--script", script_file,
        "--output", voice_file,
    ], check=True)

    print("\n─── Step 4  Render (merge + subs + burn) ────────────────")
    subprocess.run([
        py, os.path.join(steps, "step4_render.py"),
        "--video", video_path,
        "--audio", voice_file,
        "--output", final_video,
    ], check=True)

    print(f"\n✅ Done: {final_video}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YouTube automation pipeline")
    parser.add_argument("videos", nargs="+", help="Input video file(s)")
    parser.add_argument("--script-ref", type=str, help="Reference script for tone/inspiration")
    parser.add_argument("--debug", action="store_true", help="Debug mode (limited frames)")
    args = parser.parse_args()

    if args.debug:
        config.DEBUG_MODE = True
        print("🐛 Debug mode enabled")

    any_errors = False
    for video in args.videos:
        ref = args.script_ref
        base, _ = os.path.splitext(video)
        local_txt = base + ".txt"
        merged = None
        if args.script_ref and os.path.isfile(local_txt):
            merged = base + "_combined_ref.txt"
            with open(args.script_ref) as g, open(local_txt) as f:
                combined = g.read().strip() + "\n\n" + f.read().strip()
            with open(merged, "w") as m:
                m.write(combined)
            ref = merged
            print(f"📄 Combined global ref + local {os.path.basename(local_txt)}")
        elif ref is None and os.path.isfile(local_txt):
            ref = local_txt
            print(f"📄 Using auto-detected script ref: {local_txt}")
        try:
            run_pipeline(video, script_ref=ref)
        except Exception as e:
            print(f"\n❌ Error processing {video}: {e}")
            any_errors = True
        finally:
            if merged and os.path.isfile(merged):
                os.remove(merged)

    if any_errors:
        sys.exit(1)
    print("\n🎯 All videos processed!")
