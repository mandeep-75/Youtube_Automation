"""
Step 5: TTS Generation using Chatterbox.
Generates voice narration from script text using Chatterbox TTS.
No background music - clean voice output only.
"""

import argparse
import os
import sys

import torchaudio as ta
import torch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


def generate_tts(
    script_text: str,
    output_path: str,
    audio_prompt_path: str = None,
    voice: str = "female",
    pitch: float = 0.0,
    speed: float = 1.0,
    emotion: str = "neutral",
) -> str:
    """
    Generate TTS audio using Chatterbox Turbo.

    Args:
        script_text: Text to synthesize
        output_path: Where to save the output audio
        audio_prompt_path: Reference audio for voice cloning
        voice: Voice preset (male, female, neutral)
        pitch: Pitch adjustment (-1.0 to 1.0)
        speed: Speech speed (0.5 to 2.0)
        emotion: Emotion preset (neutral, happy, sad, angry, fearful)

    Returns:
        Path to the generated audio file
    """
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[chatterbox-tts] Using device: {device}")

    print("[chatterbox-tts] Loading Chatterbox Turbo model...")
    model = ChatterboxTurboTTS.from_pretrained(device=device)

    # Use config audio prompt or default sample
    if audio_prompt_path is None or not os.path.exists(audio_prompt_path):
        audio_prompt_path = os.path.join(config.PROJECT_ROOT, "samples", "me.mp3")
        if not os.path.exists(audio_prompt_path):
            raise FileNotFoundError(
                "No audio prompt found. Please provide a reference audio file "
                "or place one at samples/me.mp3"
            )

    print(f"[chatterbox-tts] Using audio prompt: {audio_prompt_path}")

    # Clean script text - remove any section markers if present
    clean_script = _clean_script(script_text)

    print(f"[chatterbox-tts] Generating {len(clean_script)} chars of speech...")
    wav = model.generate(clean_script, audio_prompt_path=audio_prompt_path)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Save as WAV
    ta.save(output_path, wav, model.sr)
    print(f"[chatterbox-tts] ✅ Audio saved to: {output_path}")

    return output_path


def _clean_script(script_text: str) -> str:
    """Remove section markers and extra formatting from script."""
    import re

    # Remove section markers like [Verse], [Chorus], [Bridge], etc.
    cleaned = re.sub(r"\[(Verse|Chorus|Bridge|Pre-Chorus)\].*?\n", "", script_text)
    # Remove extra newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate narration using Chatterbox TTS"
    )
    parser.add_argument("--script", required=True, help="Input script text file")
    parser.add_argument(
        "--duration", type=float, required=True, help="Duration in seconds"
    )
    parser.add_argument(
        "--output", default="outputs/voice.wav", help="Output audio file"
    )
    parser.add_argument(
        "--audio-prompt",
        default=None,
        help="Reference audio for voice cloning",
    )
    parser.add_argument(
        "--voice",
        default=config.CHATTERBOX_VOICE,
        help="Voice preset (male, female, neutral)",
    )
    parser.add_argument(
        "--pitch",
        type=float,
        default=config.CHATTERBOX_PITCH,
        help="Pitch adjustment (-1.0 to 1.0)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=config.CHATTERBOX_SPEED,
        help="Speech speed (0.5 to 2.0)",
    )
    parser.add_argument(
        "--emotion",
        default=config.CHATTERBOX_EMOTION,
        help="Emotion preset (neutral, happy, sad, angry, fearful)",
    )

    args = parser.parse_args()

    # Read script text
    if not os.path.exists(args.script):
        print(f"[chatterbox-tts] ❌ Error: Script file not found: {args.script}")
        sys.exit(1)

    with open(args.script, "r", encoding="utf-8") as f:
        script_text = f.read()

    try:
        generate_tts(
            script_text=script_text,
            output_path=args.output,
            audio_prompt_path=args.audio_prompt,
            voice=args.voice,
            pitch=args.pitch,
            speed=args.speed,
            emotion=args.emotion,
        )
    except Exception as e:
        print(f"[chatterbox-tts] ❌ Error: {e}")
        sys.exit(1)
