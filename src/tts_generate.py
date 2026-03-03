# tts_generate.py
"""
ChatterboxTTS voice-over generator.
Runs inside the dedicated `venvs/chatterbox` venv.

Usage (via pipeline):
    python src/tts_generate.py --script outputs/script.txt --output outputs/voice.wav

Usage (direct import):
    from src.tts_generate import generate_voice
    generate_voice("Hello world", "outputs/voice.wav")
"""

import argparse
import os
import torch
import soundfile as sf
from chatterbox.tts import ChatterboxTTS

DEVICE = "cuda" if torch.cuda.is_available()  else "cpu"


def generate_voice(script_text: str, output_path: str = "outputs/voice.wav") -> None:
    """Generate a voice-over WAV from `script_text` using ChatterboxTTS."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"[tts] Loading ChatterboxTTS on device: {DEVICE}")
    model = ChatterboxTTS.from_pretrained(DEVICE)

    print(f"[tts] Generating audio for {len(script_text)} characters ...")
    wav = model.generate(
        script_text,
        exaggeration=0.7,
        temperature=0.8,
        cfg_weight=0.5,
        min_p=0.05,
        top_p=1.0,
        repetition_penalty=1.2,
    )

    sf.write(output_path, wav.squeeze(0).cpu().numpy(), model.sr)
    print(f"[tts] ✅  Voice saved to: {output_path}")


# ── CLI entry-point ────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate voice-over with ChatterboxTTS.")
    parser.add_argument("--script", required=True, help="Path to the script text file")
    parser.add_argument("--output", default="outputs/voice.wav", help="Output WAV path")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    with open(args.script, "r", encoding="utf-8") as f:
        script = f.read().strip()
    generate_voice(script, args.output)