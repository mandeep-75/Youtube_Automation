import argparse
import os
import torch
import soundfile as sf
from chatterbox.tts import ChatterboxTTS

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def generate_voice(script_text: str, output_path: str = "outputs/voice.wav",
                   ref_audio: str | None = None) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"[tts] Loading ChatterboxTTS on device: {DEVICE}")
    model = ChatterboxTTS.from_pretrained(device=DEVICE)

    print(f"[tts] Generating audio for {len(script_text)} characters ...")
    wav = model.generate(
        script_text,
        audio_prompt_path=ref_audio,
        exaggeration=0.6,
        temperature=0.05,
        cfg_weight=0.5,
        min_p=0.05,
        top_p=1.0,
        repetition_penalty=1.2,
    )

    sf.write(output_path, wav.squeeze(0).cpu().numpy(), model.sr)
    print(f"[tts] ✅ Voice saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--script",    required=True)
    parser.add_argument("--output",    default="outputs/voice.wav")
    parser.add_argument("--ref-audio", default=None)
    args = parser.parse_args()

    with open(args.script, "r", encoding="utf-8") as f:
        script = f.read().strip()

    generate_voice(script, args.output, ref_audio=args.ref_audio)