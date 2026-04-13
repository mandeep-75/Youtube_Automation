"""
Step 5: TTS Generation using Piper TTS.
Fast, lightweight, local neural text to speech.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


def download_voice(voice: str, download_dir: str) -> tuple[str, str]:
    """Download voice model from HuggingFace if not present."""
    model_path = os.path.join(download_dir, f"{voice}.onnx")
    config_path = os.path.join(download_dir, f"{voice}.onnx.json")

    if os.path.exists(model_path) and os.path.exists(config_path):
        if os.path.getsize(model_path) > 1000:
            return model_path, config_path

    os.makedirs(download_dir, exist_ok=True)

    parts = voice.split("-")
    if len(parts) >= 4:
        region = f"{parts[0]}_{parts[1]}"
        voice_name = parts[2]
        quality = parts[3] if len(parts) > 3 else "medium"
    else:
        region = "en_US"
        voice_name = "joe"
        quality = "medium"

    path = f"en/{region}/{voice_name}/{quality}"

    repo_id = "rhasspy/piper-voices"

    print(f"[piper-tts] Downloading voice: {voice}")

    from huggingface_hub import hf_hub_download

    for ext in [".onnx", ".onnx.json"]:
        filename = f"{voice}{ext}"
        dest = os.path.join(download_dir, filename)
        if not os.path.exists(dest) or os.path.getsize(dest) < 100:
            print(f"[piper-tts] Downloading {filename}...")
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=f"{path}/{filename}",
            )
            import shutil

            real_path = os.path.realpath(downloaded)
            shutil.copy(real_path, dest)
            print(f"[piper-tts] Saved to: {dest}")

    return model_path, config_path


def generate_tts(
    script_text: str,
    output_path: str,
    voice: str = None,
    download_dir: str = None,
) -> str:
    """
    Generate TTS audio using Piper TTS via piper-onnx.
    """
    from piper_onnx import Piper

    voice = voice or config.PIPER_VOICE
    download_dir = download_dir or config.PIPER_DOWNLOAD_DIR

    print(f"[piper-tts] Using voice: {voice}")
    print(f"[piper-tts] Download directory: {download_dir}")

    model_path, config_path = download_voice(voice, download_dir)

    piper = Piper(model_path, config_path)

    cleaned_script = _clean_script(script_text)
    print(f"[piper-tts] Generating {len(cleaned_script)} chars of speech...")

    audio, sample_rate = piper.create(cleaned_script)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    import wave

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((audio * 32767).astype("int16").tobytes())

    print(f"[piper-tts] Audio saved to: {output_path}")

    return output_path


def _clean_script(script_text: str) -> str:
    """Remove section markers and extra formatting from script."""
    import re

    cleaned = re.sub(r"\[(Verse|Chorus|Bridge|Pre-Chorus)\].*?\n", "", script_text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate narration using Piper TTS")
    parser.add_argument("--script", required=True, help="Input script text file")
    parser.add_argument(
        "--duration",
        type=float,
        help="Target duration (unused, kept for compatibility)",
    )
    parser.add_argument(
        "--output", default="outputs/voice.wav", help="Output audio file"
    )
    parser.add_argument(
        "--voice",
        default=config.PIPER_VOICE,
        help="Piper voice model name",
    )
    parser.add_argument(
        "--download-dir",
        default=config.PIPER_DOWNLOAD_DIR,
        help="Directory to download voice models",
    )

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"[piper-tts] Error: Script file not found: {args.script}")
        sys.exit(1)

    with open(args.script, "r", encoding="utf-8") as f:
        script_text = f.read()

    try:
        generate_tts(
            script_text=script_text,
            output_path=args.output,
            voice=args.voice,
            download_dir=args.download_dir,
        )
    except Exception as e:
        print(f"[piper-tts] Error: {e}")
        sys.exit(1)
