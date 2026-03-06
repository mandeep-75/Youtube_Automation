# pipeline.py
"""
Full YT-automation pipeline
----------------------------

Step 1a – Extract frames
Step 1b – FastVLM describe frames
Step 2  – LLM script generation
Step 3  – ChatterboxTTS voice
Step 3.5 – Merge TTS audio + video
Step 4  – Transcribe to SRT
Step 4.5 – Burn subtitles
"""

import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Python interpreters – one per environment
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

FASTVLM_PYTHON = "/opt/homebrew/Caskroom/miniforge/base/envs/fastvlm/bin/python"

CHATTERBOX_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "chatterbox", "bin", "python")
if not os.path.isfile(CHATTERBOX_PYTHON):
    CHATTERBOX_PYTHON = sys.executable

FASTER_WHISPER_PYTHON = os.path.join(
    PROJECT_ROOT, "venvs", "faster_whisper", "bin", "python"
)

if not os.path.isfile(FASTER_WHISPER_PYTHON):
    raise FileNotFoundError(
        f"\n[pipeline] faster_whisper venv not found at:\n  {FASTER_WHISPER_PYTHON}\n"
        "Run this first:\n  bash venvs/faster_whisper/setup.sh"
    )


# ---------------------------------------------------------------------------
# Shared paths
# ---------------------------------------------------------------------------

FRAMES_DIR = os.path.join(PROJECT_ROOT, "outputs", "frames")
MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    "checkpoints",
    "llava-fastvithd_1.5b_stage3",
)

FRAME_INTERVAL = "2.0"


# ══════════════════════════════════════════════════════════════════════════
# Step 1a – Extract frames
# ══════════════════════════════════════════════════════════════════════════

def run_extract_frames(video_path: str) -> str:

    os.makedirs(FRAMES_DIR, exist_ok=True)

    manifest_path = os.path.join(FRAMES_DIR, "manifest.json")

    cmd = [
        CHATTERBOX_PYTHON,
        "./src/extract_frames.py",
        "--video-file",
        video_path,
        "--interval",
        FRAME_INTERVAL,
        "--output-dir",
        FRAMES_DIR,
    ]

    print("[extract_frames]")
    subprocess.run(cmd, check=True)

    return manifest_path


# ══════════════════════════════════════════════════════════════════════════
# Step 1b – FastVLM frame description
# ══════════════════════════════════════════════════════════════════════════

def run_fastvlm_describe(manifest_path: str, output_file: str):

    cmd = [
        FASTVLM_PYTHON,
        "./src/fastvlm_describe.py",
        "--manifest",
        manifest_path,
        "--model-path",
        MODEL_PATH,
        "--output-file",
        output_file,
    ]

    print("[fastvlm_describe]")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 1c – Transcribe original video audio
# ══════════════════════════════════════════════════════════════════════════

def run_transcribe_original(video_path: str, output_file: str, model: str = "base",
                            language: str | None = None):
    """
    Whisper-transcribe the ORIGINAL input video to plain text.
    Runs inside the faster_whisper venv (same environment as transcribe_subtitles.py).
    """
    cmd = [
        FASTER_WHISPER_PYTHON,
        "./src/transcribe_original.py",
        "--video",
        video_path,
        "--output",
        output_file,
        "--model",
        model,
    ]

    if language:
        cmd += ["--language", language]

    print("[transcribe_original]")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 2 – LLM Script generation
# ══════════════════════════════════════════════════════════════════════════

def run_llm_script(frames_file: str, script_output: str,
                   transcript_file: str | None = None):

    cmd = [
        CHATTERBOX_PYTHON,
        "./src/llm_script.py",
        "--input",
        frames_file,
        "--output",
        script_output,
    ]

    if transcript_file and os.path.isfile(transcript_file):
        cmd += ["--transcript", transcript_file]

    print("[llm_script]")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 3 – TTS
# ══════════════════════════════════════════════════════════════════════════

def run_tts(script_file: str, voice_output: str):

    cmd = [
        CHATTERBOX_PYTHON,
        "./src/tts_generate.py",
        "--script",
        script_file,
        "--output",
        voice_output,
        "--ref-audio",
        "./samples/1.mp3",
    ]

    print("[tts_generate]")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 3.5 – Merge audio + video
# ══════════════════════════════════════════════════════════════════════════

def run_merge_audio_video(video_path: str, audio_path: str, output_path: str, mix: bool = False):

    cmd = [
        FASTER_WHISPER_PYTHON,
        "./src/merge_audio_video.py",
        "--video",
        video_path,
        "--audio",
        audio_path,
        "--output",
        output_path,
    ]

    if mix:
        cmd.append("--mix")

    print("[merge_audio_video]")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 4 – Transcribe subtitles
# ══════════════════════════════════════════════════════════════════════════

def run_transcribe_subtitles(video_path: str, srt_path: str, model="base", language=None):

    cmd = [
        FASTER_WHISPER_PYTHON,
        "./src/transcribe_subtitles.py",
        "--video",
        video_path,
        "--model",
        model,
        "--srt",
        srt_path,
    ]

    if language:
        cmd += ["--language", language]

    print("[transcribe_subtitles]")
    subprocess.run(cmd, check=True)

    return srt_path


# ══════════════════════════════════════════════════════════════════════════
# Step 4.5 – Burn subtitles
# ══════════════════════════════════════════════════════════════════════════

def run_burn_subtitles(video_path: str, subtitle_path: str, output_path: str):

    cmd = [
        FASTER_WHISPER_PYTHON,
        "./src/burn_subtitles.py",
        video_path,
        subtitle_path,
        "-o",
        output_path,
        "--font-name",
        "Arial",
        "--font-size",
        "24",
        "--font-color",
        "#FFFFFF",
        "--border-color",
        "#000000",
        "--border-width",
        "2",
        "--max-words",
        "3",
    ]

    print("[burn_subtitles]")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Main Pipeline
# ══════════════════════════════════════════════════════════════════════════

def main(video_path: str):

    os.makedirs("outputs", exist_ok=True)

    frames_file      = "outputs/frames.txt"
    transcript_file  = "outputs/transcript.txt"
    script_file      = "outputs/script.txt"

    voice_file = "outputs/voice.wav"

    video_with_tts = "outputs/video_with_tts.mp4"

    srt_file = "outputs/subtitles.srt"

    final_video = "outputs/final_video.mp4"

    # Step 1a
    print("\n--- Step 1a Extract Frames ---")
    manifest = run_extract_frames(video_path)

    # Step 1b
    print("\n--- Step 1b FastVLM Describe ---")
    run_fastvlm_describe(manifest, frames_file)

    # Step 1c
    print("\n--- Step 1c Transcribe Original Audio ---")
    run_transcribe_original(video_path, transcript_file)

    # Step 2
    print("\n--- Step 2 LLM Script ---")
    run_llm_script(frames_file, script_file, transcript_file=transcript_file)

    # Step 3
    print("\n--- Step 3 Generate Voice ---")
    run_tts(script_file, voice_file)

    # Step 3.5
    print("\n--- Step 3.5 Merge Audio + Video ---")
    run_merge_audio_video(video_path, voice_file, video_with_tts)

    # Step 4
    print("\n--- Step 4 Transcribe Video ---")
    run_transcribe_subtitles(video_with_tts, srt_file)

    # Step 4.5
    print("\n--- Step 4.5 Burn Subtitles ---")
    run_burn_subtitles(video_with_tts, srt_file, final_video)

    print("\nPipeline finished!")
    print("Final video:", final_video)


# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "video",
        help="Input video file",
    )

    args = parser.parse_args()

    main(args.video)



