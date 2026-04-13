import os
import argparse
import json
import ollama
from tqdm import tqdm


def describe_frame(client, image_path, model, prompt):
    """Send a single image to Ollama for description."""
    try:
        stream = client.generate(
            model=model,
            think=False,
            prompt=prompt,
            keep_alive="15s",
            images=[image_path],
            stream=True,
        )

        response_text = []
        for chunk in stream:
            token = chunk.get("response", "")
            if token:
                response_text.append(token)

        return "".join(response_text).strip()

    except Exception as e:
        return f"[Error: {e}]"


def main(args):
    with open(args.manifest, "r", encoding="utf-8") as f:
        entries = json.load(f)

    print(f"\n🚀 Vision: {len(entries)} frames with {args.model}")

    base_host = (
        args.ollama_url.split("/api")[0]
        if "/api" in args.ollama_url
        else args.ollama_url
    )
    client = ollama.Client(host=base_host)

    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)

    with open(args.output_file, "w", encoding="utf-8") as f:
        for entry in tqdm(entries, desc="Describing Frames"):
            image_path = entry["path"]
            timestamp = entry["timestamp"]

            if not os.path.isfile(image_path):
                tqdm.write(f"⚠️ Image not found, skipping: {image_path}")
                continue

            description = describe_frame(client, image_path, args.model, args.prompt)

            line = f"{timestamp} - {description}"
            f.write(line + "\n")
            f.flush()

    print(f"\n✅ Saved to: {args.output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Describe images via Ollama SDK.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument(
        "--context-window",
        type=int,
        default=5,
        help="Number of previous frames to include as context (default: 5)",
    )

    args = parser.parse_args()
    main(args)
