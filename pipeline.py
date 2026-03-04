# pipeline.py
"""
Full YT-automation pipeline
----------------------------
Step 1a  – Extract frames          → chatterbox venv  (has OpenCV)
Step 1b  – FastVLM describe        → fastvlm   conda env
Step 2   – LLM script generation   → chatterbox venv  (has Gemini/OpenAI client)
Step 3   – ChatterboxTTS voice     → chatterbox venv  (TTS engine)
Step 3.5 – Merge TTS audio + video → faster_whisper venv (ffmpeg)
Step 4   – Transcribe to SRT       → faster_whisper venv (faster-whisper)
Step 4.5 – Burn subtitles          → faster_whisper venv (FFmpeg + pysubs2)
"""

import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Python interpreters – one per environment
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# FastVLM lives in a separate conda env (no cv2 conflict)
FASTVLM_PYTHON = "/opt/homebrew/Caskroom/miniforge/base/envs/fastvlm/bin/python"


# Chatterbox venv (TTS + frame extraction + LLM calls)
CHATTERBOX_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "chatterbox", "bin", "python")
# Fallback: if the venv hasn't been built yet, stay in the current interpreter
if not os.path.isfile(CHATTERBOX_PYTHON):
    CHATTERBOX_PYTHON = sys.executable

# faster-whisper venv (transcription + subtitle burning)
FASTER_WHISPER_PYTHON = os.path.join(PROJECT_ROOT, "venvs", "faster_whisper", "bin", "python")
if not os.path.isfile(FASTER_WHISPER_PYTHON):
    raise FileNotFoundError(
        f"\n[pipeline] faster_whisper venv not found at:\n  {FASTER_WHISPER_PYTHON}\n"
        "Run this first:\n  bash venvs/faster_whisper/setup.sh"
    )

# ---------------------------------------------------------------------------
# Shared paths
# ---------------------------------------------------------------------------
FRAMES_DIR     = os.path.join(PROJECT_ROOT, "outputs", "frames")
MODEL_PATH     = os.path.join(PROJECT_ROOT, "checkpoints", "llava-fastvithd_0.5b_stage3")
FRAME_INTERVAL = "2.0"
PROMPT         = "Describe what is happening in this frame in two lines."


# ══════════════════════════════════════════════════════════════════════════
# Step 1a – Extract frames (OpenCV, chatterbox venv)
# ══════════════════════════════════════════════════════════════════════════

def run_extract_frames(video_path: str, frames_dir: str = FRAMES_DIR) -> str:
    """
    Extract frames from the video using cv2.
    Runs with CHATTERBOX_PYTHON (the venv that has OpenCV installed).
    Produces PNGs + a manifest.json inside `frames_dir`.
    Returns the path to manifest.json.
    """
    manifest_path = os.path.join(frames_dir, "manifest.json")
    cmd = [
        CHATTERBOX_PYTHON, "./src/extract_frames.py",
        "--video-file", video_path,
        "--interval",   FRAME_INTERVAL,
        "--output-dir", frames_dir,
    ]
    print(f"  [extract_frames] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return manifest_path


# ══════════════════════════════════════════════════════════════════════════
# Step 1b – FastVLM inference (fastvlm conda env)
# ══════════════════════════════════════════════════════════════════════════

def run_fastvlm_describe(manifest_path: str, output_file: str) -> None:
    """
    Run FastVLM inference on the pre-extracted frames.
    Runs with FASTVLM_PYTHON (fastvlm conda env that has llava).
    No cv2 import happens here – no package conflict.
    """
    cmd = [
        FASTVLM_PYTHON, "./src/fastvlm_describe.py",
        "--manifest",    manifest_path,
        "--model-path",  MODEL_PATH,
        "--output-file", output_file,
        "--prompt",      PROMPT,
    ]
    print(f"  [fastvlm_describe] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 2 – LLM script generation (chatterbox venv)
# ══════════════════════════════════════════════════════════════════════════

def run_llm_script(frames_file: str, script_output: str) -> None:
    """
    Generate a cinematic script from frame descriptions.
    Runs in the chatterbox venv using CHATTERBOX_PYTHON.
    """
    cmd = [
        CHATTERBOX_PYTHON, "./src/llm_script.py",
        "--input",  frames_file,
        "--output", script_output,
    ]
    print(f"  [llm_script] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 3 – ChatterboxTTS voice-over (chatterbox venv, subprocess)
# ══════════════════════════════════════════════════════════════════════════

def run_tts(script_file: str, voice_output: str) -> None:
    """
    Runs tts_generate.py inside the dedicated chatterbox venv so that
    the TTS engine's heavy dependencies are fully isolated.
    """
    cmd = [
        CHATTERBOX_PYTHON, "./src/tts_generate.py",
        "--script", script_file,
        "--output", voice_output,
        "--ref-audio", "./samples/1.mp3",  # Optional: add an audio prompt to influence the voice
    ]
    print(f"  [tts] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 3.5 – Merge TTS audio + original video (faster_whisper venv)
# ══════════════════════════════════════════════════════════════════════════

def run_merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    mix: bool = False,
) -> None:
    """
    Merges the TTS voice-over (audio_path) onto the original video (video_path).
    Uses the faster_whisper venv which has ffmpeg bundled via imageio_ffmpeg.

    Args:
        video_path:  Original silent (or existing audio) video.
        audio_path:  TTS WAV file from ChatterboxTTS.
        output_path: Output MP4 with voice-over baked in.
        mix:         If True, mix TTS with original audio instead of replacing.
    """
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/merge_audio_video.py",
        "--video",  video_path,
        "--audio",  audio_path,
        "--output", output_path,
    ]
    if mix:
        cmd.append("--mix")
    print(f"  [merge_audio_video] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 4 – Transcribe to SRT (faster_whisper venv, subprocess)
# ══════════════════════════════════════════════════════════════════════════

def run_transcribe_subtitles(
    video_path: str,
    model: str = "base",
    language: str | None = None,
    srt_path: str | None = None,
) -> str:
    """
    Transcribes the video with faster-whisper and exports to SRT.
    Returns the path to the generated SRT file.
    
    Subtitle burning is now handled separately by burn_subtitles.py
    for better modularity and customization options.
    Runs inside the isolated `venvs/faster_whisper` venv.

    Args:
        video_path:  Input video file.
        model:       Whisper model size (tiny/base/small/medium/large-v3).
        language:    Force a language code, e.g. "en". None = auto-detect.
        srt_path:    Path where to save the SRT subtitle file.
    """
    if not srt_path:
        raise ValueError("srt_path is required for subtitle export")
    
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/transcribe_subtitles.py",
        "--video",  video_path,
        "--model",  model,
        "--srt",    srt_path,
    ]
    if language:
        cmd += ["--language", language]

    print(f"  [transcribe_subtitles] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return srt_path


# ══════════════════════════════════════════════════════════════════════════
# Step 4.5 – Burn subtitles (faster_whisper venv, subprocess)
# ══════════════════════════════════════════════════════════════════════════

def run_burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    font_name: str = "Arial",
    font_size: int = 36,
    font_color: str = "FFFFFF",
    border_color: str = "000000",
    border_width: int = 2,
    karaoke: bool = False,
    word_per_line: bool = False,
) -> None:
    """
    Burn subtitles using burn_subtitles.py
    Supports:
        - Normal grouped
        - Karaoke mode
        - Word-per-line mode
    """

    cmd = [
        FASTER_WHISPER_PYTHON, "./src/burn_subtitles.py",
        video_path,
        subtitle_path,
        "-o", output_path,
        "--font-name", font_name,
        "--font-size", str(font_size),
        "--font-color", f"#{font_color}",
        "--highlight-color", "#FFFF00",
        "--border-color", f"#{border_color}",
        "--border-width", str(border_width),
        "--margin-v", "80",
    ]

    if karaoke:
        cmd.append("--karaoke")

    if word_per_line:
        cmd.append("--word-per-line")

    print(f"  [burn_subtitles] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

# ══════════════════════════════════════════════════════════════════════════
# Main pipeline
# ══════════════════════════════════════════════════════════════════════════

def main(
    video_path: str,
    burn_style: bool = False,
    custom_font: str | None = None,
    custom_font_size: int | None = None,
) -> None:
    os.makedirs("outputs", exist_ok=True)

    frames_file        = "outputs/frames.txt"
    script_file        = "outputs/script.txt"
    voice_file         = "outputs/voice.wav"
    # Step 3.5 output: original video + TTS audio baked in
    video_with_tts     = "outputs/video_with_tts.mp4"
    # Step 4 output: SRT subtitle file
    srt_file           = "outputs/subtitles.srt"
    # Step 4.5 output: video with burned subtitles
    subtitled_video    = "outputs/final_video.mp4"
    # Step 4.5 output (optional): re-styled subtitled video
    styled_video       = "outputs/final_video_styled.mp4"

    # ---------- 1a. Extract frames ----------
    print("\n──── Step 1a: Extracting frames (chatterbox venv) ────")
    manifest = run_extract_frames(video_path)

    # ---------- 1b. Describe frames ----------
    print("\n──── Step 1b: Describing frames (fastvlm env) ────")
    run_fastvlm_describe(manifest, frames_file)

    # ---------- 2. Generate script ----------
    print("\n──── Step 2: Generating script (LLM) ────")
    run_llm_script(frames_file, script_file)

    # ---------- 3. Generate voice-over ----------
    print("\n──── Step 3: Generating voice (chatterbox venv) ────")
    run_tts(script_file, voice_file)

    # ---------- 3.5. Merge TTS audio + original video ----------
    print("\n──── Step 3.5: Merging TTS audio onto video (faster_whisper venv) ────")
    run_merge_audio_video(
        video_path=video_path,
        audio_path=voice_file,
        output_path=video_with_tts,
        mix=False,   # True = mix with original audio; False = replace it
    )

    # ---------- 4. Transcribe merged video + export subtitles ----------
    print("\n──── Step 4: Transcribing video & exporting SRT (faster_whisper venv) ────")
    # We transcribe *video_with_tts* — it has the TTS audio so subtitles
    # will match exactly what the voice-over says.
    run_transcribe_subtitles(
        video_path=video_with_tts,
        model="base",    # change to "small" or "medium" for higher accuracy
        language=None,   # None = auto-detect
        srt_path=srt_file,
    )

    # ---------- 4.5. Burn subtitles onto video ----------
    print("\n──── Step 4.5: Burning subtitles onto video (faster_whisper venv) ────")
    # Determine final output based on styling flag
    final_output = styled_video if burn_style else subtitled_video
    
    run_burn_subtitles(
        video_path=video_with_tts,
        subtitle_path=srt_file,
        output_path=final_output,
        font_name=custom_font or "Arial",
        font_size=custom_font_size or 24,
        font_color="FFFFFF",      # white
        border_color="000000",    # black
        border_width=2,
        soft=False,              # hard burn for final output
        preset="fast",
    )

    print(f"\n✅  Pipeline complete!")
    print(f"    Merged (video+TTS) : {video_with_tts}")
    print(f"    SRT subtitles      : {srt_file}")
    print(f"    Final output       : {final_output}")
    print(f"    Voice-over         : {voice_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Full YT automation pipeline: frames → LLM → voice-over → subtitles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python pipeline.py input_video.mp4

  # Run pipeline with custom subtitle styling
  python pipeline.py input_video.mp4 --burn-style --font "DejaVu Sans" --font-size 28

  # Quiet mode (default)
  python pipeline.py input_video.mp4
        """,
    )

    parser.add_argument("video", help="Input video file")
    parser.add_argument(
        "--burn-style",
        action="store_true",
        help="Apply custom subtitle styling after transcription (Step 4.5)",
    )
    parser.add_argument(
        "--font",
        type=str,
        default=None,
        help="Font name for custom subtitle styling (default: Arial)",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=None,
        help="Font size for custom subtitle styling (default: 24)",
    )

    args = parser.parse_args()

    main(
        video_path=args.video,
        burn_style=args.burn_style,
        custom_font=args.font,
        custom_font_size=args.font_size,
    )