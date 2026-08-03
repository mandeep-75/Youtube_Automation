import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


def generate_tts(
    script_text: str,
    output_path: str,
    ref_audio: str | None = None,
    ref_text: str | None = None,
) -> str:
    import torch
    from qwen_tts import Qwen3TTSModel
    import soundfile as sf

    model_path = os.path.join(config.PROJECT_ROOT, "models", "qwen3-tts", "Qwen3-TTS-12Hz-1.7B-Base")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "mps" else torch.float32
    print(f"[tts] Loading model: {model_path} (device={device}, dtype={dtype})")
    model = Qwen3TTSModel.from_pretrained(model_path, device_map=device, dtype=dtype)

    ref_audio = ref_audio or config.TTS_REF_AUDIO
    if ref_text is None:
        ref_text_file = getattr(config, "TTS_REF_TEXT_FILE", "")
        if ref_text_file and os.path.exists(ref_text_file):
            with open(ref_text_file, "r", encoding="utf-8") as f:
                ref_text = f.read().strip()
        else:
            ref_text = getattr(config, "TTS_REF_TEXT", "")

    if not ref_audio or not os.path.exists(ref_audio):
        print(f"[tts] Error: Reference audio not found: {ref_audio}")
        print(f"[tts] Provide a voice reference with TTS_REF_AUDIO in config or --ref-audio arg")
        sys.exit(1)

    print(f"[tts] Generating {len(script_text)} chars, ref_audio={ref_audio}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    wavs, sr = model.generate_voice_clone(
        text=script_text,
        language="English",
        ref_audio=ref_audio,
        ref_text=ref_text,
    )

    sf.write(output_path, wavs[0], sr)
    print(f"[tts] Audio saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TTS audio via Qwen3 voice clone")
    parser.add_argument("--script", required=True, help="Input script text file")
    parser.add_argument("--output", default="outputs/voice.wav", help="Output audio file")
    parser.add_argument("--ref-audio", default=None, help="Reference audio for voice clone")
    parser.add_argument("--ref-text", default=None, help="Transcript of reference audio")

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
            ref_audio=args.ref_audio,
            ref_text=args.ref_text,
        )
    except Exception as e:
        print(f"[tts] Error: {e}")
        sys.exit(1)
