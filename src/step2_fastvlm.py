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
from llava.constants import (
    IMAGE_TOKEN_INDEX,
    DEFAULT_IMAGE_TOKEN,
    DEFAULT_IM_START_TOKEN,
    DEFAULT_IM_END_TOKEN,
)


def build_prompt(prompt_text: str, model, conv_mode: str) -> str:
    if model.config.mm_use_im_start_end:
        qs = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN + "\n" + prompt_text
    else:
        qs = DEFAULT_IMAGE_TOKEN + "\n" + prompt_text

    conv = conv_templates[conv_mode].copy()
    conv.append_message(conv.roles[0], qs)
    conv.append_message(conv.roles[1], None)
    return conv.get_prompt()


def load_frames_from_manifest(manifest_path: str):
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

    prompt_text = args.prompt.replace(DEFAULT_IMAGE_TOKEN, "").lstrip()
    prompt = build_prompt(prompt_text, model, args.conv_mode)
    input_ids = tokenizer_image_token(
        prompt,
        tokenizer,
        IMAGE_TOKEN_INDEX,
        return_tensors="pt"
    ).unsqueeze(0).to(device)

    input_token_len = input_ids.shape[1]

    print("\nStarting frame description...\n")

    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)

    with open(args.output_file, "w", encoding="utf-8") as f:
        for idx, image in enumerate(tqdm(frames)):
            image_tensor = process_images(
                [image],
                image_processor,
                model.config
            )[0]

            with torch.inference_mode():
                output_ids = model.generate(
                    input_ids,
                    images=image_tensor.unsqueeze(0).to(device).half()
                        if device.type != "cpu"
                        else image_tensor.unsqueeze(0).to(device),
                    image_sizes=[image.size],
                    do_sample=True,
                    temperature=0.2,
                    top_p=None,
                    num_beams=1,
                    max_new_tokens=256,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                    use_cache=True,
                )
            new_tokens = output_ids[:, input_token_len:]
            text_output = tokenizer.batch_decode(
                new_tokens,
                skip_special_tokens=True
            )[0].strip()

            line = f"{timestamps[idx]} - {text_output}"
            print("→", line, flush=True)
            f.write(line + "\n")
            f.flush()

    print(f"\nDone ✅ Output saved to {args.output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", type=str,
                        default="Describe this frame in two sentences.")
    parser.add_argument("--manifest", type=str, required=True)
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--model-base", type=str, default=None)
    parser.add_argument("--conv-mode", type=str, default="qwen_2")
    parser.add_argument("--output-file", type=str, default="outputs/frames.txt")

    args = parser.parse_args()
    main(args)