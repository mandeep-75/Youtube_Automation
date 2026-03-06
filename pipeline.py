import os
import subprocess
import sys
from pathlib import Path

from config import (
    PROJECT_ROOT,
    OLLAMA_URL,
    FRAME_INTERVAL,
    VISION_MODEL,
    VISION_PROMPT,
    WHISPER_MODEL,
    WHISPER_LANG,
    WHISPER_BEAM_SIZE,
    WHISPER_COMPUTE_TYPE,
    LLM_MODEL,
    TTS_REF_AUDIO,
    TTS_EXAGGERATION,
    TTS_TEMPERATURE,
    TTS_CFG_WEIGHT,
    TTS_REPETITION_PENALTY,
    MERGE_MIX_AUDIO,
    ORIGINAL_AUDIO_VOLUME,
    SUBTITLE_FONT_NAME,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_FONT_COLOR,
    SUBTITLE_HIGHLIGHT_COLOR,
    SUBTITLE_BORDER_COLOR,
    SUBTITLE_BORDER_WIDTH,
    SUBTITLE_MAX_WORDS,
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

def step1_extract_frames(video_path: str, frames_dir: str) -> str:
    os.makedirs(frames_dir, exist_ok=True)
    manifest_path = os.path.join(frames_dir, "manifest.json")
    subprocess.run([
        CHATTERBOX_PYTHON, "./src/step1_extract_frames.py",
        "--video-file", video_path,
        "--interval",   FRAME_INTERVAL,
        "--output-dir", frames_dir,
    ], check=True)
    return manifest_path

def step2_vision_describe(manifest_path: str, output_file: str):
    subprocess.run([
        CHATTERBOX_PYTHON, "./src/step2_qwen_vl.py",
        "--manifest",     manifest_path,
        "--model",        VISION_MODEL,
        "--prompt",       VISION_PROMPT,
        "--output-file",  output_file,
        "--ollama-url",   OLLAMA_URL,
    ], check=True)

def step3_transcribe_original(video_path: str, output_file: str):
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/step3_transcribe_original.py",
        "--video",        video_path,
        "--output",       output_file,
        "--model",        WHISPER_MODEL,
        "--beam-size",    str(WHISPER_BEAM_SIZE),
        "--compute-type", WHISPER_COMPUTE_TYPE,
    ]
    if WHISPER_LANG:
        cmd += ["--language", WHISPER_LANG]
    subprocess.run(cmd, check=True)

def step4_llm_script(frames_file: str, transcript_file: str, script_output: str):
    cmd = [
        CHATTERBOX_PYTHON, "./src/step4_llm_script.py",
        "--input",      frames_file,
        "--output",     script_output,
        "--model",      LLM_MODEL,
        "--ollama-url", OLLAMA_URL,
    ]
    if transcript_file and os.path.isfile(transcript_file):
        cmd += ["--transcript", transcript_file]
    subprocess.run(cmd, check=True)

def step5_tts(script_file: str, voice_output: str):
    subprocess.run([
        CHATTERBOX_PYTHON, "./src/step5_tts.py",
        "--script",             script_file,
        "--output",             voice_output,
        "--ref-audio",          TTS_REF_AUDIO,
        "--exaggeration",       str(TTS_EXAGGERATION),
        "--temperature",        str(TTS_TEMPERATURE),
        "--cfg-weight",         str(TTS_CFG_WEIGHT),
        "--repetition-penalty", str(TTS_REPETITION_PENALTY),
    ], check=True)

def step6_merge_av(video_path: str, audio_path: str, output_path: str):
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/step6_merge_av.py",
        "--video",  video_path,
        "--audio",  audio_path,
        "--output", output_path,
        "--volume", str(ORIGINAL_AUDIO_VOLUME),
    ]
    if MERGE_MIX_AUDIO:
        cmd.append("--mix")
    subprocess.run(cmd, check=True)

def step7_transcribe_subtitles(video_path: str, srt_path: str):
    cmd = [
        FASTER_WHISPER_PYTHON, "./src/step7_transcribe_subtitles.py",
        "--video",        video_path,
        "--model",        WHISPER_MODEL,
        "--srt",          srt_path,
        "--beam-size",    str(WHISPER_BEAM_SIZE),
        "--compute-type", WHISPER_COMPUTE_TYPE,
    ]
    if WHISPER_LANG:
        cmd += ["--language", WHISPER_LANG]
    subprocess.run(cmd, check=True)

def step8_burn_subtitles(video_path: str, subtitle_path: str, output_path: str):
    subprocess.run([
        FASTER_WHISPER_PYTHON, "./src/step8_burn_subtitles.py",
        video_path, subtitle_path,
        "-o",               output_path,
        "--font-name",       SUBTITLE_FONT_NAME,
        "--font-size",       str(SUBTITLE_FONT_SIZE),
        "--font-color",      SUBTITLE_FONT_COLOR,
        "--highlight-color", SUBTITLE_HIGHLIGHT_COLOR,
        "--border-color",    SUBTITLE_BORDER_COLOR,
        "--border-width",    str(SUBTITLE_BORDER_WIDTH),
        "--max-words",       str(SUBTITLE_MAX_WORDS),
    ], check=True)

def run_pipeline(video_path: str):
    video_name = Path(video_path).stem
    out_dir = os.path.join(PROJECT_ROOT, "outputs", video_name)
    os.makedirs(out_dir, exist_ok=True)

    frames_dir      = os.path.join(out_dir, "frames")
    frames_file     = os.path.join(out_dir, "frames.txt")
    transcript_file = os.path.join(out_dir, "transcript.txt")
    script_file     = os.path.join(out_dir, "script.txt")
    voice_file      = os.path.join(out_dir, "voice.wav")
    video_tts       = os.path.join(out_dir, "video_with_tts.mp4")
    srt_file        = os.path.join(out_dir, "subtitles.srt")
    final_video     = os.path.join(out_dir, "final_video.mp4")

    print(f"\n🚀 Processing video: {video_path}")
    print(f"📂 Output directory: {out_dir}")

    print("\n─── Step 1  Extract frames ───────────────────────────────────")
    manifest = step1_extract_frames(video_path, frames_dir)

    print("\n─── Step 2  Vision frame descriptions ────────────────────────")
    step2_vision_describe(manifest, frames_file)

    print("\n─── Step 3  Transcribe original audio ────────────────────────")
    step3_transcribe_original(video_path, transcript_file)

    print("\n─── Step 4  Generate narration script ────────────────────────")
    step4_llm_script(frames_file, transcript_file, script_file)

    print("\n─── Step 5  Text-to-speech ───────────────────────────────────")
    step5_tts(script_file, voice_file)

    print("\n─── Step 6  Merge TTS audio onto video ───────────────────────")
    step6_merge_av(video_path, voice_file, video_tts)

    print("\n─── Step 7  Transcribe TTS for subtitles ─────────────────────")
    step7_transcribe_subtitles(video_tts, srt_file)

    print("\n─── Step 8  Burn subtitles ───────────────────────────────────")
    step8_burn_subtitles(video_tts, srt_file, final_video)

    print(f"\n✅ Finished processing: {video_path}")
    print(f"   Final video: {final_video}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YouTube automation pipeline")
    parser.add_argument("videos", nargs="+", help="Input video file(s)")
    args = parser.parse_args()

    for video in args.videos:
        try:
            run_pipeline(video)
        except Exception as e:
            print(f"\n❌ Error processing {video}: {e}")
            continue

    print("\n🎯 All videos processed!")
