# pipeline.py
"""
Full YT-automation pipeline
----------------------------
Step 1a  – Extract frames          → chatterbox venv  (has OpenCV)
Step 1b  – FastVLM describe        → fastvlm   conda env
Step 2   – LLM script generation   → chatterbox venv  (has Gemini/OpenAI client)
Step 3   – ChatterboxTTS voice     → chatterbox venv  (TTS engine)
Step 3.5 – Merge TTS audio + video → faster_whisper venv (ffmpeg)
Step 4   – Transcribe + subtitles  → faster_whisper venv (faster-whisper + MoviePy)
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
# Step 4 – Transcribe + burn subtitles (faster_whisper venv, subprocess)
# ══════════════════════════════════════════════════════════════════════════

def run_transcribe_subtitles(
    video_path: str,
    output_path: str,
    model: str = "base",
    language: str | None = None,
    srt_path: str | None = None,
) -> None:
    """
    Transcribes the video with faster-whisper and burns timed subtitles
    directly onto the output video.
    Runs inside the isolated `venvs/faster_whisper` venv.

    Args:
        video_path:  Input video (the voice-over video from step 3, or any mp4).
        output_path: Where to write the final subtitled mp4.
        model:       Whisper model size (tiny/base/small/medium/large-v3).
        language:    Force a language code, e.g. "en". None = auto-detect.
        srt_path:    Optional path to also save a .srt file.
    """
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/transcribe_subtitles.py",
        "--video",  video_path,
        "--output", output_path,
        "--model",  model,
    ]
    if language:
        cmd += ["--language", language]
    if srt_path:
        cmd += ["--srt", srt_path]

    print(f"  [transcribe_subtitles] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


# ══════════════════════════════════════════════════════════════════════════
# Main pipeline
# ══════════════════════════════════════════════════════════════════════════

def main(video_path: str) -> None:
    os.makedirs("outputs", exist_ok=True)

    frames_file        = "outputs/frames.txt"
    script_file        = "outputs/script.txt"
    voice_file         = "outputs/voice.wav"
    # Step 3.5 output: original video + TTS audio baked in
    video_with_tts     = "outputs/video_with_tts.mp4"
    # Step 4 output: subtitled final video
    subtitled_video    = "outputs/final_video.mp4"
    srt_file           = "outputs/subtitles.srt"

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

    # ---------- 4. Transcribe merged video + burn subtitles ----------
    print("\n──── Step 4: Transcribing & burning subtitles (faster_whisper venv) ────")
    # We transcribe *video_with_tts* — it has the TTS audio so subtitles
    # will match exactly what the voice-over says.
    run_transcribe_subtitles(
        video_path=video_with_tts,
        output_path=subtitled_video,
        model="base",    # change to "small" or "medium" for higher accuracy
        language=None,   # None = auto-detect
        srt_path=srt_file,
    )

    print(f"\n✅  Pipeline complete!")
    print(f"    Merged (video+TTS) : {video_with_tts}")
    print(f"    Final subtitled    : {subtitled_video}")
    print(f"    SRT file           : {srt_file}")
    print(f"    Voice-over         : {voice_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <video_path>")
        sys.exit(1)
    main(sys.argv[1])