import os
import random
import re
import subprocess
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src import config

# Validate environment
if not os.path.isfile(config.CHATTERBOX_PYTHON):
    print(
        f"⚠️ Warning: Chatterbox venv not found at {config.CHATTERBOX_PYTHON}. Using current interpreter."
    )
    config.CHATTERBOX_PYTHON = sys.executable

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
            config.CHATTERBOX_PYTHON,
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
        config.UPLOADER_PYTHON,
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
        config.UPLOADER_PYTHON,
        "./src/steps/step4_llm_script.py",
        "--input",
        frames_file,
        "--output",
        script_output,
        "--duration",
        f"{duration:.2f}",
        "--wps",
        str(config.LLM_WORDS_PER_SECOND),
        "--model",
        config.LLM_MODEL,
        "--ollama-url",
        config.OLLAMA_URL,
    ]
    if transcript_file and os.path.isfile(transcript_file):
        cmd += ["--transcript", transcript_file]
    subprocess.run(cmd, check=True)


def step5_tts(script_file: str, voice_output: str):
    ref_audio = config.TTS_REF_AUDIO
    print(f"🎤 Using TTS reference audio: {ref_audio}")
    subprocess.run(
        [
            config.CHATTERBOX_PYTHON,
            "./src/steps/step5_tts.py",
            "--script",
            script_file,
            "--output",
            voice_output,
            "--ref-audio",
            ref_audio,
            "--exaggeration",
            str(config.TTS_EXAGGERATION),
            "--temperature",
            str(config.TTS_TEMPERATURE),
            "--cfg-weight",
            str(config.TTS_CFG_WEIGHT),
            "--repetition-penalty",
            str(config.TTS_REPETITION_PENALTY),
        ],
        check=True,
    )


def step5_5_generate_bgm(
    script_file: str,
    duration: float,
    output_path: str,
    comfyui_url: str = None,
):
    """Generate background music using ACE-Step 1.5 via ComfyUI."""
    cmd = [
        config.UNIFIED_PYTHON,
        "./src/steps/step5_5_bgm.py",
        "--script",
        script_file,
        "--duration",
        f"{duration:.2f}",
        "--output",
        output_path,
        "--infer-style",
    ]
    if comfyui_url:
        cmd += ["--comfyui-url", comfyui_url]

    print(f"🎵 Generating background music via ACE-Step 1.5...")
    subprocess.run(cmd, check=True)


def step5_6_mix_audio(
    narration_path: str,
    music_path: str,
    output_path: str,
    narration_volume: float = 1.0,
    music_volume: float = 0.25,
):
    """Mix TTS narration with background music."""
    cmd = [
        config.UNIFIED_PYTHON,
        "./src/steps/step5_6_mix_audio.py",
        "--narration",
        narration_path,
        "--music",
        music_path,
        "--output",
        output_path,
        "--narration-volume",
        str(narration_volume),
        "--music-volume",
        str(music_volume),
        "--fade-in",
        str(config.MUSIC_FADE_IN),
        "--fade-out",
        str(config.MUSIC_FADE_OUT),
    ]

    print(f"🎛️  Mixing narration with background music...")
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
    # Replace spaces with underscores, remove invalid chars
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing dots and spaces
    name = name.strip(". ")
    # Ensure not empty
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


def run_pipeline(video_path: str, with_bgm: bool = True):
    """
    Run the full video processing pipeline.

    Args:
        video_path: Path to input video
        with_bgm: Whether to generate background music (requires ComfyUI + ACE-Step)
    """
    # Use full filename (including tags and extension) for the output directory
    video_name = os.path.basename(video_path)
    video_name = sanitize_filename(video_name)
    out_dir = os.path.join(config.PROJECT_ROOT, "yt_inbox", "outputs", video_name)
    os.makedirs(out_dir, exist_ok=True)

    frames_dir = os.path.join(out_dir, "frames")
    frames_file = os.path.join(out_dir, "frames.txt")
    transcript_file = os.path.join(out_dir, "transcript.txt")
    script_file = os.path.join(out_dir, "script.txt")
    voice_file = os.path.join(out_dir, "voice.wav")
    bgm_file = os.path.join(out_dir, "bgm.wav")
    mixed_audio = os.path.join(out_dir, "mixed_audio.wav")

    # Two video versions (mixed and simple)
    video_mixed = os.path.join(out_dir, "video_mixed.mp4")
    video_simple = os.path.join(out_dir, "video_simple.mp4")

    # Subtitles for each version
    srt_mixed = os.path.join(out_dir, "subtitles_mixed.srt")
    srt_simple = os.path.join(out_dir, "subtitles_simple.srt")

    # Final videos for each version
    final_video_mixed = os.path.join(out_dir, "final_video_mixed.mp4")
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

    print("\n─── Step 5  Text-to-speech ───────────────────────────────────")
    step5_tts(script_file, voice_file)

    # Step 5.5 - Generate background music (optional)
    if with_bgm:
        print("\n─── Step 5.5  Generate background music ──────────────────────")
        try:
            step5_5_generate_bgm(
                script_file=script_file,
                duration=duration,
                output_path=bgm_file,
                comfyui_url=config.COMFYUI_URL,
            )

            print("\n─── Step 5.6  Mix audio with background music ───────────────")
            step5_6_mix_audio(
                narration_path=voice_file,
                music_path=bgm_file,
                output_path=mixed_audio,
                narration_volume=1.0,
                music_volume=config.MUSIC_VOLUME,
            )
            # Use mixed audio for the simple version
            audio_for_simple = mixed_audio
        except Exception as e:
            print(f"⚠️ Background music generation failed: {e}")
            print("   Falling back to TTS-only audio...")
            audio_for_simple = voice_file
    else:
        audio_for_simple = voice_file

    print("\n─── Step 6  Merge TTS audio onto video ───────────────────────")
    print("   [Mixed version] Original + TTS audio...")
    step6_merge_av(video_path, voice_file, video_mixed, mix_audio=True)

    print("   [Simple version] TTS (with/without BGM)...")
    step6_merge_av(video_path, audio_for_simple, video_simple, mix_audio=False)

    print("\n─── Step 7  Transcribe TTS for subtitles ─────────────────────")
    print("   [Mixed version] Transcribing...")
    step7_transcribe_subtitles(video_mixed, srt_mixed)
    print("   [Simple version] Transcribing...")
    step7_transcribe_subtitles(video_simple, srt_simple)

    print("\n─── Step 8  Burn subtitles ───────────────────────────────────")
    print("   [Mixed version] Burning subtitles...")
    step8_burn_subtitles(video_mixed, srt_mixed, final_video_mixed)
    print("   [Simple version] Burning subtitles...")
    step8_burn_subtitles(video_simple, srt_simple, final_video_simple)

    # Clean up intermediate files (video + subtitle files used for burning)
    cleanup_intermediate_files(video_mixed, video_simple, srt_mixed, srt_simple)

    print(f"\n✅ Finished processing: {video_path}")
    print(f"   Mixed video:  {final_video_mixed}")
    print(f"   Simple video: {final_video_simple}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube automation pipeline")
    parser.add_argument("videos", nargs="+", help="Input video file(s)")
    parser.add_argument(
        "--no-bgm", action="store_true", help="Skip background music generation"
    )
    args = parser.parse_args()

    any_errors = False
    for video in args.videos:
        try:
            run_pipeline(video, with_bgm=not args.no_bgm)
        except Exception as e:
            print(f"\n❌ Error processing {video}: {e}")
            any_errors = True
            continue

    if any_errors:
        print("\n⚠️ Some videos failed to process.")
        sys.exit(1)

    print("\n🎯 All videos processed!")
