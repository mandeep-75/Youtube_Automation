import argparse
import os
import torch
import soundfile as sf
from chatterbox.tts import ChatterboxTTS

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def generate_voice(script_text: str, output_path: str = "outputs/voice.wav",
                   ref_audio: str | None = None,
                   exaggeration: float = 0.6,
                   temperature: float = 0.05,
                   cfg_weight: float = 0.5,
                   repetition_penalty: float = 1.2) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"[tts] Loading ChatterboxTTS on device: {DEVICE}")
    model = ChatterboxTTS.from_pretrained(device=DEVICE)

    print(f"[tts] Generating audio for {len(script_text)} characters ...")
    wav = model.generate(
        script_text,
        audio_prompt_path=ref_audio,
        exaggeration=exaggeration,
        temperature=temperature,
        cfg_weight=cfg_weight,
        min_p=0.05,
        top_p=1.0,
        repetition_penalty=repetition_penalty,
    )

    sf.write(output_path, wav.squeeze(0).cpu().numpy(), model.sr)
    print(f"[tts] ✅ Voice saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--script",             required=True)
    parser.add_argument("--output",             default="outputs/voice.wav")
    parser.add_argument("--ref-audio",          default=None)
    parser.add_argument("--exaggeration",       type=float, default=0.6)
    parser.add_argument("--temperature",        type=float, default=0.05)
    parser.add_argument("--cfg-weight",         type=float, default=0.5)
    parser.add_argument("--repetition-penalty", type=float, default=1.2)
    args = parser.parse_args()

    with open(args.script, "r", encoding="utf-8") as f:
        script = f.read().strip()

    generate_voice(
        script,
        args.output,
        ref_audio=args.ref_audio,
        exaggeration=args.exaggeration,
        temperature=args.temperature,
        cfg_weight=args.cfg_weight,
        repetition_penalty=args.repetition_penalty
    )