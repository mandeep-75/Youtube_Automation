import os
import subprocess
import sys

from config import (
    PROJECT_ROOT,
    FRAME_INTERVAL,
    FASTVLM_MODEL_PATH,
    FASTVLM_PROMPT,
    WHISPER_MODEL,
    WHISPER_LANG,
    LLM_MODEL,
    TTS_REF_AUDIO,
    MERGE_MIX_AUDIO,
    SUBTITLE_FONT_NAME,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_FONT_COLOR,
    SUBTITLE_BORDER_COLOR,
    SUBTITLE_BORDER_WIDTH,
    SUBTITLE_MAX_WORDS,
    FASTVLM_PYTHON,
    CHATTERBOX_PYTHON,
    FASTER_WHISPER_PYTHON,
)

if not os.path.isfile(CHATTERBOX_PYTHON):
    CHATTERBOX_PYTHON = sys.executable

if not os.path.isfile(FASTER_WHISPER_PYTHON):
    raise FileNotFoundError(
        f"\n[pipeline] faster_whisper venv not found at:\n  {FASTER_WHISPER_PYTHON}\n"
        "Run:  bash venvs/faster_whisper/setup.sh"
    )

FRAMES_DIR      = os.path.join(PROJECT_ROOT, "outputs", "frames")
FRAMES_FILE     = "outputs/frames.txt"
TRANSCRIPT_FILE = "outputs/transcript.txt"
SCRIPT_FILE     = "outputs/script.txt"
VOICE_FILE      = "outputs/voice.wav"
VIDEO_TTS       = "outputs/video_with_tts.mp4"
SRT_FILE        = "outputs/subtitles.srt"
FINAL_VIDEO     = "outputs/final_video.mp4"


def step1_extract_frames(video_path: str) -> str:
    os.makedirs(FRAMES_DIR, exist_ok=True)
    manifest_path = os.path.join(FRAMES_DIR, "manifest.json")
    subprocess.run([
        CHATTERBOX_PYTHON, "./src/step1_extract_frames.py",
        "--video-file", video_path,
        "--interval",   FRAME_INTERVAL,
        "--output-dir", FRAMES_DIR,
    ], check=True)
    return manifest_path


def step2_fastvlm(manifest_path: str, output_file: str):
    subprocess.run([
        FASTVLM_PYTHON, "./src/step2_fastvlm.py",
        "--manifest",    manifest_path,
        "--model-path",  FASTVLM_MODEL_PATH,
        "--output-file", output_file,
        "--prompt",      FASTVLM_PROMPT,
    ], check=True)


def step3_transcribe_original(video_path: str, output_file: str):
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/step3_transcribe_original.py",
        "--video",  video_path,
        "--output", output_file,
        "--model",  WHISPER_MODEL,
    ]
    if WHISPER_LANG:
        cmd += ["--language", WHISPER_LANG]
    subprocess.run(cmd, check=True)


def step4_llm_script(frames_file: str, transcript_file: str, script_output: str):
    cmd = [
        CHATTERBOX_PYTHON, "./src/step4_llm_script.py",
        "--input",  frames_file,
        "--output", script_output,
        "--model",  LLM_MODEL,
    ]
    if transcript_file and os.path.isfile(transcript_file):
        cmd += ["--transcript", transcript_file]
    subprocess.run(cmd, check=True)


def step5_tts(script_file: str, voice_output: str):
    subprocess.run([
        CHATTERBOX_PYTHON, "./src/step5_tts.py",
        "--script",    script_file,
        "--output",    voice_output,
        "--ref-audio", TTS_REF_AUDIO,
    ], check=True)


def step6_merge_av(video_path: str, audio_path: str, output_path: str):
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/step6_merge_av.py",
        "--video",  video_path,
        "--audio",  audio_path,
        "--output", output_path,
    ]
    if MERGE_MIX_AUDIO:
        cmd.append("--mix")
    subprocess.run(cmd, check=True)


def step7_transcribe_subtitles(video_path: str, srt_path: str):
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/step7_transcribe_subtitles.py",
        "--video", video_path,
        "--model", WHISPER_MODEL,
        "--srt",   srt_path,
    ]
    if WHISPER_LANG:
        cmd += ["--language", WHISPER_LANG]
    subprocess.run(cmd, check=True)


def step8_burn_subtitles(video_path: str, subtitle_path: str, output_path: str):
    subprocess.run([
        FASTER_WHISPER_PYTHON, "./src/step8_burn_subtitles.py",
        video_path, subtitle_path,
        "-o",             output_path,
        "--font-name",    SUBTITLE_FONT_NAME,
        "--font-size",    SUBTITLE_FONT_SIZE,
        "--font-color",   SUBTITLE_FONT_COLOR,
        "--border-color", SUBTITLE_BORDER_COLOR,
        "--border-width", SUBTITLE_BORDER_WIDTH,
        "--max-words",    SUBTITLE_MAX_WORDS,
    ], check=True)


def main(video_path: str):
    os.makedirs("outputs", exist_ok=True)

    print("\n─── Step 1  Extract frames ───────────────────────────────────")
    manifest = step1_extract_frames(video_path)

    print("\n─── Step 2  FastVLM frame descriptions ───────────────────────")
    step2_fastvlm(manifest, FRAMES_FILE)

    print("\n─── Step 3  Transcribe original audio ────────────────────────")
    step3_transcribe_original(video_path, TRANSCRIPT_FILE)

    print("\n─── Step 4  Generate narration script ────────────────────────")
    step4_llm_script(FRAMES_FILE, TRANSCRIPT_FILE, SCRIPT_FILE)

    print("\n─── Step 5  Text-to-speech ───────────────────────────────────")
    step5_tts(SCRIPT_FILE, VOICE_FILE)

    print("\n─── Step 6  Merge TTS audio onto video ───────────────────────")
    step6_merge_av(video_path, VOICE_FILE, VIDEO_TTS)

    print("\n─── Step 7  Transcribe TTS for subtitles ─────────────────────")
    step7_transcribe_subtitles(VIDEO_TTS, SRT_FILE)

    print("\n─── Step 8  Burn subtitles ───────────────────────────────────")
    step8_burn_subtitles(VIDEO_TTS, SRT_FILE, FINAL_VIDEO)

    print("\n✅ Pipeline finished!")
    print("   Final video:", FINAL_VIDEO)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YouTube automation pipeline")
    parser.add_argument("video", help="Input video file")
    main(parser.parse_args().video)
