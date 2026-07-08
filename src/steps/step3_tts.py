import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


def generate_tts(script_text: str, output_path: str, voice: str = None, speed: float = None) -> str:
    from kittentts import KittenTTS

    voice = voice or config.TTS_VOICE
    speed = speed if speed is not None else config.TTS_SPEED

    print(f"[tts] Loading model: {config.TTS_MODEL}")
    model = KittenTTS(config.TTS_MODEL)

    print(f"[tts] Generating {len(script_text)} chars, voice={voice}, speed={speed}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    model.generate_to_file(script_text, output_path, voice=voice, speed=speed)

    print(f"[tts] Audio saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TTS audio using Kitten TTS")
    parser.add_argument("--script", required=True, help="Input script text file")
    parser.add_argument("--output", default="outputs/voice.wav", help="Output audio file")
    parser.add_argument("--voice", default=None, help="Voice name (default: config.TTS_VOICE)")
    parser.add_argument("--speed", type=float, default=None, help="Speech speed (default: config.TTS_SPEED)")

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"[tts] Error: Script file not found: {args.script}")
        sys.exit(1)

    with open(args.script, "r", encoding="utf-8") as f:
        script_text = f.read()

    try:
        generate_tts(
            script_text=script_text,
            output_path=args.output,
            voice=args.voice,
            speed=args.speed,
        )
    except Exception as e:
        print(f"[tts] Error: {e}")
        sys.exit(1)
