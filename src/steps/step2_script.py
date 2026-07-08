import gc
import os
import shutil
import subprocess
import sys
import tempfile

from faster_whisper import WhisperModel

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_LOCAL_FFMPEG = os.path.join(_PROJECT_ROOT, "tools", "ffmpeg")
if os.path.isfile(_LOCAL_FFMPEG) and os.access(_LOCAL_FFMPEG, os.X_OK):
    FFMPEG_BIN = _LOCAL_FFMPEG
else:
    try:
        import imageio_ffmpeg

        FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_path() -> str:
    probe = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(probe):
        probe = shutil.which("ffprobe") or "ffprobe"
    return probe


def _has_audio(video_path: str) -> bool:
    try:
        result = subprocess.run(
            [
                _ffprobe_path(),
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True


def _format_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def transcribe_original(video_path: str, output_path: str) -> str:
    if not _has_audio(video_path):
        print("[transcribe] ⚠️ No audio stream – writing empty transcript.")
        with open(output_path, "w") as f:
            pass
        return output_path

    tmp = tempfile.mkdtemp(prefix="orig_audio_")
    wav = os.path.join(tmp, "audio.wav")
    try:
        subprocess.run(
            [
                FFMPEG_BIN,
                "-y",
                "-i",
                video_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "wav",
                wav,
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )

        model = WhisperModel(
            config.WHISPER_MODEL,
            device="auto",
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        segments, info = model.transcribe(
            wav,
            language=config.WHISPER_LANG,
            beam_size=config.WHISPER_BEAM_SIZE,
            word_timestamps=False,
        )
        lines = [f"[{_format_ts(s.start)}] {s.text.strip()}" for s in segments]
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[transcribe] ✅ Saved to {output_path} ({len(lines)} segments)")
        return output_path
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if "model" in locals():
            del model
        gc.collect()


SCRIPT_PROMPT = """You are a viral YouTube Shorts scriptwriter who specializes in high-retention cinematic storytelling.

Your narration should feel like a friend telling an unbelievable real story directly to the camera late at night — intense, curious, and impossible to scroll past.

INPUT DATA

VIDEO DURATION: {duration} seconds
TARGET WORD COUNT: {target_words} words
AVERAGE SPEECH RATE: {wps} words per second

VISUAL SEQUENCE (chronological frame descriptions):
{vision_text}

ORIGINAL DIALOGUE (optional):
{transcript_text}

REFERENCE SCRIPT (optional):
{ref_text}

IMPORTANT CONTEXT

The visual descriptions represent frames from one continuous video in chronological order.

Do not mention frames or describe them individually.

Instead:
• Combine all visuals into one flowing narrative
• Infer actions, reactions, and emotions
• Tell the story naturally as events unfold

Use dialogue only if it strengthens the story.

TONE & STYLE

The voice should feel:
• Cinematic
• Conversational
• High-energy

Write using short, punchy sentences to maintain fast pacing.

The story must remain YouTube-friendly and advertiser safe.

Avoid:
• Profanity
• Hate speech
• Sexual content
• Political messaging

STORY STRUCTURE

Hook (first sentence)

The first sentence must immediately stop the scroll.

It must begin with one of these phrases:
"This..."

WRITING RULES

• Write one continuous paragraph
• Do not use bullet points in the script
• Do not add labels or timestamps
• Do not repeat the visual descriptions word-for-word
• Focus on action, reactions, and suspense
• Maintain fast pacing for Shorts

REFERENCE SCRIPT GUIDANCE

If a reference script is provided above, match its tone, pacing, and style — do not copy its content.
Emulate the energy, sentence structure, and delivery style.

LENGTH & PACING

The script must match the video duration.

Target word count: approximately {target_words} words.
Aim to meet or come close to this target.

OUTPUT FORMAT

Return only the final narration script as plain text.

Do not include explanations or formatting.
"""


def generate_script(
    frames_file: str,
    transcript_file: str,
    script_file: str,
    duration: float,
    script_ref: str | None = None,
) -> None:
    with open(frames_file, "r", encoding="utf-8") as f:
        vision_data = f.read()

    transcript_data = None
    if transcript_file and os.path.isfile(transcript_file):
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_data = f.read()

    transcript_val = (
        transcript_data.strip() if transcript_data else "[No audio script available]"
    )

    ref_text = "[No reference script provided]"
    if script_ref and os.path.isfile(script_ref):
        with open(script_ref, "r", encoding="utf-8") as f:
            ref_text = f.read().strip()

    target_words = int(duration * config.LLM_WORDS_PER_SECOND)

    prompt = SCRIPT_PROMPT.format(
        duration=duration,
        wps=config.LLM_WORDS_PER_SECOND,
        target_words=target_words,
        transcript_text=transcript_val,
        vision_text=vision_data.strip(),
        ref_text=ref_text,
    )

    import ollama

    print(f"[script] Calling Ollama {config.LLM_MODEL}...")
    client = ollama.Client(host=config.OLLAMA_URL)
    stream = client.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        options={"num_predict": 4000, "num_ctx": 8192},
        keep_alive=0,
        stream=True,
    )

    response_text = []
    thinking_text = []
    in_thinking = False

    for chunk in stream:
        if hasattr(chunk, "message"):
            msg = chunk.message
            thought = getattr(msg, "thinking", "") or ""
            content = getattr(msg, "content", "") or ""
        else:
            msg = chunk.get("message", {})
            thought = msg.get("thinking", "") or ""
            content = msg.get("content", "") or ""

        if thought:
            if not in_thinking:
                print("\nThinking:\n", end="", flush=True)
                in_thinking = True
            print(thought, end="", flush=True)
            thinking_text.append(thought)

        if content:
            if in_thinking:
                print("\n\nAnswer:\n", end="", flush=True)
                in_thinking = False
            print(content, end="", flush=True)
            response_text.append(content)

    print()
    final_script = "".join(response_text).strip()
    final_thinking = "".join(thinking_text).strip()

    with open(script_file, "w", encoding="utf-8") as f:
        f.write(final_script or "[Error: Model returned empty script]")
    print(f"[script] Saved to {script_file}")

    if final_thinking:
        think_path = script_file.replace(".txt", ".thinking.txt")
        with open(think_path, "w", encoding="utf-8") as f:
            f.write(final_thinking)
        print(f"[script] Thinking saved to {think_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--frames-file", required=True)
    parser.add_argument("--transcript-file", required=True)
    parser.add_argument("--script-file", required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument(
        "--script-ref", type=str, help="Reference script for tone/inspiration"
    )
    args = parser.parse_args()

    transcribe_original(args.video, args.transcript_file)
    generate_script(
        args.frames_file,
        args.transcript_file,
        args.script_file,
        args.duration,
        script_ref=args.script_ref,
    )
