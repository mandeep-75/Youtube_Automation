import os
import random
import re
import subprocess
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src import config

# Validate environment
if not os.path.isfile(config.FASTER_WHISPER_PYTHON):
    raise FileNotFoundError(
        f"\n[pipeline] faster_whisper venv not found at:\n  {config.FASTER_WHISPER_PYTHON}\n"
        "Please ensure the virtual environment is set up correctly."
    )


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe. Raises if duration cannot be determined."""
    ffprobe_bin = os.path.join(config.PROJECT_ROOT, "tools", "ffprobe")
    if not (os.path.isfile(ffprobe_bin) and os.access(ffprobe_bin, os.X_OK)):
        ffprobe_bin = "ffprobe"

    result = subprocess.run(
        [
            ffprobe_bin,
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
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError(f"Invalid duration {duration} for video: {video_path}")
    return duration


def step1_extract_frames(video_path: str, frames_dir: str) -> str:
    os.makedirs(frames_dir, exist_ok=True)
    manifest_path = os.path.join(frames_dir, "manifest.json")
    subprocess.run(
        [
            config.UNIFIED_PYTHON,
            "./src/steps/step1_extract_frames.py",
            "--video-file",
            video_path,
            "--interval",
            config.FRAME_INTERVAL,
            "--output-dir",
            frames_dir,
        ],
        check=True,
    )
    return manifest_path


def step2_vision_describe(
    manifest_path: str, output_file: str, hallucination_check: bool = False
):
    cmd = [
        config.UNIFIED_PYTHON,
        "./src/steps/step2_qwen_vl.py",
        "--manifest",
        manifest_path,
        "--model",
        config.VISION_MODEL,
        "--prompt",
        config.VISION_PROMPT,
        "--output-file",
        output_file,
        "--ollama-url",
        config.OLLAMA_URL,
        "--context-window",
        str(config.VISION_CONTEXT_WINDOW),
    ]
    if hallucination_check:
        cmd.append("--hallucination-check")
    subprocess.run(cmd, check=True)


def step3_transcribe_original(video_path: str, output_file: str):
    cmd = [
        config.FASTER_WHISPER_PYTHON,
        "./src/steps/step3_transcribe_original.py",
        "--video",
        video_path,
        "--output",
        output_file,
        "--model",
        config.WHISPER_MODEL,
        "--beam-size",
        str(config.WHISPER_BEAM_SIZE),
        "--compute-type",
        config.WHISPER_COMPUTE_TYPE,
    ]
    if config.WHISPER_LANG:
        cmd += ["--language", config.WHISPER_LANG]
    subprocess.run(cmd, check=True)


def step4_llm_script(
    frames_file: str, transcript_file: str, script_output: str, duration: float
):
    cmd = [
        config.UNIFIED_PYTHON,
        "./src/steps/step4_llm_script.py",
        "--input",
        frames_file,
        "--output",
        script_output,
        "--duration",
        f"{duration:.2f}",
        "--wps",
        str(config.LLM_WORDS_PER_SECOND),
        "--music-style",
        config.MUSIC_STYLE,
        "--model",
        config.LLM_MODEL,
        "--ollama-url",
        config.OLLAMA_URL,
    ]
    if transcript_file and os.path.isfile(transcript_file):
        cmd += ["--transcript", transcript_file]
    subprocess.run(cmd, check=True)


def step5_tts(script_file: str, voice_output: str, duration: float):
    """
    Generate narration with background music using ACE-Step 1.5.
    The script becomes the lyrics, and ACE-Step generates vocals + music.
    """
    print("🎵 Generating narration with ACE-Step 1.5...")
    cmd = [
        config.UNIFIED_PYTHON,
        "./src/steps/step5_tts.py",
        "--script",
        script_file,
        "--duration",
        f"{duration:.2f}",
        "--output",
        voice_output,
        "--style",
        config.MUSIC_STYLE,
        "--comfyui-url",
        config.COMFYUI_URL,
    ]
    subprocess.run(cmd, check=True)


def step6_merge_av(
    video_path: str, audio_path: str, output_path: str, mix_audio: Optional[bool] = None
) -> None:
    if mix_audio is None:
        mix_audio = config.MERGE_MIX_AUDIO

    cmd = [
        config.FASTER_WHISPER_PYTHON,
        "./src/steps/step6_merge_av.py",
        "--video",
        video_path,
        "--audio",
        audio_path,
        "--output",
        output_path,
        "--volume",
        str(config.ORIGINAL_AUDIO_VOLUME),
    ]
    if mix_audio:
        cmd.append("--mix")
    subprocess.run(cmd, check=True)


def step7_transcribe_subtitles(video_path: str, srt_path: str):
    cmd = [
        config.FASTER_WHISPER_PYTHON,
        "./src/steps/step7_transcribe_subtitles.py",
        "--video",
        video_path,
        "--model",
        config.WHISPER_MODEL,
        "--srt",
        srt_path,
        "--beam-size",
        str(config.WHISPER_BEAM_SIZE),
        "--compute-type",
        config.WHISPER_COMPUTE_TYPE,
    ]
    if config.WHISPER_LANG:
        cmd += ["--language", config.WHISPER_LANG]
    subprocess.run(cmd, check=True)


def step8_burn_subtitles(video_path: str, subtitle_path: str, output_path: str):
    font_choice = (
        random.choice(config.SUBTITLE_FONTS)
        if isinstance(config.SUBTITLE_FONTS, list)
        else config.SUBTITLE_FONTS
    )
    if isinstance(font_choice, dict):
        font_name = font_choice["name"]
        font_size = font_choice.get("size", 36)
    else:
        font_name = font_choice
        font_size = 36

    print(f"🔤 Using subtitle font: {font_name} (Size: {font_size})")
    cmd = [
        config.FASTER_WHISPER_PYTHON,
        "./src/steps/step8_burn_subtitles.py",
        video_path,
        subtitle_path,
        "-o",
        output_path,
        "--font-name",
        font_name,
        "--font-size",
        str(font_size),
        "--font-color",
        config.SUBTITLE_FONT_COLOR,
        "--highlight-color",
        config.SUBTITLE_HIGHLIGHT_COLOR,
        "--border-color",
        config.SUBTITLE_OUTLINE_COLOR,
        "--border-width",
        str(config.SUBTITLE_OUTLINE_WIDTH),
        "--max-words",
        str(config.SUBTITLE_MAX_WORDS),
        "--position",
        config.SUBTITLE_POSITION,
        "--x-offset",
        str(config.SUBTITLE_X_OFFSET),
        "--y-offset",
        str(config.SUBTITLE_Y_OFFSET),
    ]
    if config.SUBTITLE_BOLD:
        cmd.append("--bold")
    else:
        cmd.append("--no-bold")

    if config.SUBTITLE_ITALIC:
        cmd.append("--italic")

    subprocess.run(cmd, check=True)


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filesystem paths."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    if not name:
        name = "unnamed_video"
    return name


def cleanup_intermediate_files(*files: str) -> None:
    """Remove intermediate files that are no longer needed."""
    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"   🗑️  Removed intermediate: {os.path.basename(f)}")
            except OSError as e:
                print(f"   ⚠️  Could not remove {f}: {e}")


def run_pipeline(video_path: str):
    """
    Run the full video processing pipeline.
    Step 5 uses ACE-Step 1.5 to generate narration (with vocals) + background music.
    """
    video_name = os.path.basename(video_path)
    video_name = sanitize_filename(video_name)
    out_dir = os.path.join(config.PROJECT_ROOT, "yt_inbox", "outputs", video_name)
    os.makedirs(out_dir, exist_ok=True)

    frames_dir = os.path.join(out_dir, "frames")
    frames_file = os.path.join(out_dir, "frames.txt")
    transcript_file = os.path.join(out_dir, "transcript.txt")
    script_file = os.path.join(out_dir, "script.txt")
    voice_file = os.path.join(out_dir, "voice.wav")

    video_simple = os.path.join(out_dir, "video_simple.mp4")
    srt_simple = os.path.join(out_dir, "subtitles_simple.srt")
    final_video_simple = os.path.join(out_dir, "final_video_simple.mp4")

    print(f"\n🚀 Processing video: {video_path}")
    print(f"📂 Output directory: {out_dir}")

    print("\n─── Step 1  Extract frames ───────────────────────────────────")
    manifest = step1_extract_frames(video_path, frames_dir)

    print("\n─── Step 2  Vision frame descriptions ────────────────────────")
    step2_vision_describe(
        manifest, frames_file, hallucination_check=config.VISION_HALLUCINATION_CHECK
    )

    print("\n─── Step 3  Transcribe original audio ────────────────────────")
    step3_transcribe_original(video_path, transcript_file)

    print("\n─── Step 4  Generate narration script ────────────────────────")
    duration = get_video_duration(video_path)
    step4_llm_script(frames_file, transcript_file, script_file, duration)

    print("\n─── Step 5  Generate narration + music (ACE-Step 1.5) ──────")
    step5_tts(script_file, voice_file, duration)

    print("\n─── Step 6  Merge audio onto video ────────────────────────────")
    step6_merge_av(video_path, voice_file, video_simple, mix_audio=False)

    print("\n─── Step 7  Transcribe for subtitles ─────────────────────────")
    step7_transcribe_subtitles(video_simple, srt_simple)

    print("\n─── Step 8  Burn subtitles ───────────────────────────────────")
    step8_burn_subtitles(video_simple, srt_simple, final_video_simple)

    cleanup_intermediate_files(video_simple, srt_simple)

    print(f"\n✅ Finished processing: {video_path}")
    print(f"   Output: {final_video_simple}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube automation pipeline")
    parser.add_argument("videos", nargs="+", help="Input video file(s)")
    args = parser.parse_args()

    any_errors = False
    for video in args.videos:
        try:
            run_pipeline(video)
        except Exception as e:
            print(f"\n❌ Error processing {video}: {e}")
            any_errors = True
            continue

    if any_errors:
        print("\n⚠️ Some videos failed to process.")
        sys.exit(1)

    print("\n🎯 All videos processed!")
