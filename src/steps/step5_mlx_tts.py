"""
Step 5: TTS Generation using MLX Qwen3-TTS.
Apple Silicon optimized text to speech with voice cloning.
"""

import argparse
from typing import Optional

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


def generate_tts(
    script_text: str,
    output_path: str,
    ref_audio: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    """Generate TTS audio using MLX Qwen3-TTS."""
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio

    # Apply config defaults if not provided
    ref_audio = ref_audio or config.MLX_TTS_REF_AUDIO
    model_name = model_name or config.MLX_TTS_MODEL

    print(f"[mlx-tts] Using model: {model_name}")
    print(f"[mlx-tts] Reference audio: {ref_audio}")

    if not os.path.exists(ref_audio):
        raise FileNotFoundError(f"Reference audio not found: {ref_audio}")

    print("[mlx-tts] Loading model...")
    model = load_model(model_name)

    cleaned_script = _clean_script(script_text)
    print(f"[mlx-tts] Generating {len(cleaned_script)} chars of speech...")

    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    file_prefix = os.path.splitext(os.path.basename(output_path))[0]

    print(f"[mlx-tts] Output dir: {output_dir}")
    print(f"[mlx-tts] File prefix: {file_prefix}")

    # Change to output_dir so mlx-audio saves there
    os.chdir(output_dir)

    generate_audio(
        model=model,
        text=cleaned_script,
        ref_audio=ref_audio,
        file_prefix=file_prefix,
        output_dir=output_dir,
    )

    # Search ONLY in output_dir (current dir after chdir)
    all_files = os.listdir(".")
    wavs = [f for f in all_files if f.endswith(".wav")]

    if not wavs:
        raise RuntimeError(
            f"TTS generation failed - no wav files in {output_dir}\nAll files: {all_files}"
        )

    generated_path = sorted(wavs, key=lambda f: os.path.getmtime(f))[-1]
    print(f"[mlx-tts] Found: {generated_path}")

    if generated_path != output_path:
        import shutil

        shutil.move(generated_path, output_path)

    print(f"[mlx-tts] Audio saved to: {output_path}")
    return output_path


def _clean_script(script_text: str) -> str:
    """Remove section markers and extra formatting from script."""
    import re

    cleaned = re.sub(r"\[(Verse|Chorus|Bridge|Pre-Chorus)\].*?\n", "", script_text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate narration using MLX Qwen3-TTS"
    )
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
        "--ref-audio",
        default=None,
        help="Reference audio for voice cloning (default: config.MLX_TTS_REF_AUDIO)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="MLX TTS model name (default: config.MLX_TTS_MODEL)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"[mlx-tts] Error: Script file not found: {args.script}")
        sys.exit(1)

    with open(args.script, "r", encoding="utf-8") as f:
        script_text = f.read()

    try:
        generate_tts(
            script_text=script_text,
            output_path=args.output,
            ref_audio=args.ref_audio,
            model_name=args.model,
        )
    except Exception as e:
        print(f"[mlx-tts] Error: {e}")
        sys.exit(1)
