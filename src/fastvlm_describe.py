# fastvlm_describe.py
# Purpose: Read pre-extracted frames (PNGs) and run FastVLM inference to generate descriptions.
# Run this with the fastvlm conda env (which has llava packages installed).
# Does NOT use cv2 at all — images are loaded from disk via PIL.
# Reads a JSON manifest produced by extract_frames.py.

import os
import argparse
import json
import torch
from PIL import Image
from tqdm import tqdm

from llava.utils import disable_torch_init
from llava.conversation import conv_templates
from llava.model.builder import load_pretrained_model
from llava.mm_utils import tokenizer_image_token, process_images, get_model_name_from_path
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN


def build_prompt(prompt_text: str, model, conv_mode: str) -> str:
    qs = prompt_text
    if model.config.mm_use_im_start_end:
        qs = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN + "\n" + qs
    else:
        qs = DEFAULT_IMAGE_TOKEN + "\n" + qs
    conv = conv_templates[conv_mode].copy()
    conv.append_message(conv.roles[0], qs)
    conv.append_message(conv.roles[1], None)
    return conv.get_prompt()


def load_frames_from_manifest(manifest_path: str):
    """Load PIL images and timestamps from a manifest JSON produced by extract_frames.py."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    frames = []
    timestamps = []
    for entry in entries:
        image = Image.open(entry["path"]).convert("RGB")
        frames.append(image)
        timestamps.append(entry["timestamp"])

    print(f"Loaded {len(frames)} frames from manifest: {manifest_path}")
    return frames, timestamps


def main(args):
    disable_torch_init()

    device = torch.device(
        "mps" if torch.backends.mps.is_available()
        else "cuda" if torch.cuda.is_available()
        else "cpu"
    )
    print(f"Using device: {device}")

    model_path = os.path.expanduser(args.model_path)
    model_name = get_model_name_from_path(model_path)
    print("Loading FastVLM model...")
    tokenizer, model, image_processor, context_len = load_pretrained_model(
        model_path, args.model_base, model_name, device=device
    )
    model.generation_config.pad_token_id = tokenizer.pad_token_id

    frames, timestamps = load_frames_from_manifest(args.manifest)

    prompt = build_prompt(args.prompt, model, args.conv_mode)
    input_ids = tokenizer_image_token(
        prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt"
    ).unsqueeze(0).to(device)

    print("Starting frame description...\n")
    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
    with open(args.output_file, "w", encoding="utf-8") as f:
        for idx, image in enumerate(tqdm(frames)):
            image_tensor = process_images([image], image_processor, model.config)[0]
            with torch.inference_mode():
                output_ids = model.generate(
                    input_ids,
                    images=image_tensor.unsqueeze(0).to(device).half(),
                    image_sizes=[image.size],
                    do_sample=True if args.temperature > 0 else False,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    num_beams=args.num_beams,
                    max_new_tokens=args.max_tokens,
                    use_cache=True,
                )
            text_output = tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].strip()
            line = f"{timestamps[idx]} - {text_output}"
            print("→", line, flush=True)
            f.write(line + "\n")
            f.flush()

    print(f"\nDone ✅  Output saved to {args.output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run FastVLM inference on pre-extracted frames (run in the fastvlm conda env)."
    )
    parser.add_argument("--manifest", type=str, required=True,
                        help="Path to manifest.json produced by extract_frames.py.")
    parser.add_argument("--model-path", type=str, required=True,
                        help="Path to the FastVLM model checkpoint directory.")
    parser.add_argument("--model-base", type=str, default=None)
    parser.add_argument("--prompt", type=str,
                        default="Describe what is happening in this frame in two lines.")
    parser.add_argument("--conv-mode", type=str, default="qwen_2")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top_p", type=float, default=None)
    parser.add_argument("--num_beams", type=int, default=1)
    parser.add_argument("--max_tokens", type=int, default=256)
    parser.add_argument("--output-file", type=str, default="outputs/frames.txt",
                        help="Output text file with timestamped descriptions.")
    args = parser.parse_args()
    main(args)
