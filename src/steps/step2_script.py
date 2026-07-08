import gc
import os
import shutil
import subprocess
import sys
import tempfile

from faster_whisper import WhisperModel  # type: ignore[import-untyped]

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_LOCAL_FFMPEG = os.path.join(_PROJECT_ROOT, "tools", "ffmpeg")
if os.path.isfile(_LOCAL_FFMPEG) and os.access(_LOCAL_FFMPEG, os.X_OK):
    FFMPEG_BIN = _LOCAL_FFMPEG
else:
    try:
        import imageio_ffmpeg  # type: ignore[import-untyped]

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


SCRIPT_PROMPT = """You are a YouTube Shorts narrator. Your job is to describe what is happening in the video clearly and naturally — as if you are watching it with a friend and explaining it in real time.

INPUT

VIDEO DURATION: {duration} seconds
TARGET WORD COUNT: {target_words} words
AVERAGE SPEECH RATE: {wps} words per second

FRAME DESCRIPTIONS (in chronological order):
{vision_text}

ORIGINAL AUDIO (if any):
{transcript_text}

REFERENCE SCRIPT (for tone guidance):
{ref_text}

GUIDELINES

1. HOOK — Begin with "This..." followed by a straightforward description of the main action or subject visible in the opening moments. Be direct. Do not invent drama or mystery that is not present in the video.

2. NARRATIVE FLOW — Describe the scene in a natural order that matches the video timeline. Start with what is most noticeable, then move through what happens or what is revealed as the video progresses. End when the video ends.

3. VOICE & STYLE — Write in a conversational, spoken style. Use short, punchy sentences that are easy to read aloud. Avoid formal documentary tone or news reporter cadence. The narration should feel like someone describing what they are seeing in real time.

4. WHAT TO FOCUS ON — Focus on the main subject and the primary action. Do not list every object, color, or background detail. If the frame descriptions repeat details across consecutive frames, mention that detail once and move on. Prioritize what is most visually prominent.

5. ACCURACY — Only describe what is actually visible. Do not invent causes, locations, backstory, or events that are not shown. If context is unclear, simply describe what is in frame without speculating.

6. ENDING — End naturally when the video ends. Do not add commentary, conclusions, or forced twists. Let the final visual speak for itself.

7. SAFETY — Keep content YouTube-friendly. No profanity, hate speech, sexual content, or political messaging.

8. FORMATTING — Write as one continuous paragraph. No bullet points, numbered lists, timestamps, or labels. No explanations outside the narration.

9. WORD COUNT — Aim for approximately {target_words} words to match the {duration}-second video at {wps} words per second.

10. REFERENCE SCRIPT — If a reference script is provided, match its general tone, pacing, and energy. Do not copy its content or phrasing.

OUTPUT: Return only the final narration as plain text with no additional formatting or commentary.
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
        print(f"[script] Reference text loaded ({len(ref_text)} chars): {ref_text[:200]}")

    target_words = int(duration * config.LLM_WORDS_PER_SECOND)

    prompt = SCRIPT_PROMPT.format(
        duration=duration,
        wps=config.LLM_WORDS_PER_SECOND,
        target_words=target_words,
        transcript_text=transcript_val,
        vision_text=vision_data.strip(),
        ref_text=ref_text,
    )

    prompt_file = script_file.replace(".txt", ".prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"[script] Full prompt saved to {prompt_file}")

    import ollama

    print(f"[script] Calling Ollama {config.LLM_MODEL}...")
    client = ollama.Client(host=config.OLLAMA_URL)
    stream = client.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        options={"num_predict": 2048, "num_ctx": 8192, "repeat_penalty": 1.3, "temperature": 0.7},
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
