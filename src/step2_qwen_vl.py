import os
import argparse
import json
import ollama
from tqdm import tqdm


def describe_batch(client, image_paths, model, prompt):
    """
    Sends multiple images to Ollama in ONE request to avoid
    repeated model initialization.
    """

    try:
        stream = client.generate(
            model=model,
            prompt=prompt,
            keep_alive="15s",
            images=image_paths,
            stream=True,
        )

        response_text = []
        in_thinking = False

        for chunk in stream:

            # thinking tokens
            thought = chunk.get("thinking", "")
            if thought:
                if not in_thinking:
                    print("\nThinking:\n", end="", flush=True)
                    in_thinking = True
                print(thought, end="", flush=True)

            # answer tokens
            token = chunk.get("response", "")
            if token:
                if in_thinking:
                    print("\n\nAnswer:\n", end="", flush=True)
                    in_thinking = False

                response_text.append(token)
                print(token, end="", flush=True)

        print()
        return "".join(response_text).strip()

    except Exception as e:
        return f"[Error: {e}]"


def main(args):

    with open(args.manifest, "r", encoding="utf-8") as f:
        entries = json.load(f)

    tqdm.write(f"\n🚀 Starting Vision: {len(entries)} frames")
    tqdm.write(f"🤖 Model: {args.model}")

    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)

    # Create Ollama client once
    base_host = args.ollama_url.split("/api")[0] if "/api" in args.ollama_url else args.ollama_url
    client = ollama.Client(host=base_host)

    with open(args.output_file, "w", encoding="utf-8") as f:

        for entry in tqdm(entries, desc="Describing Frames"):

            image_path = entry["path"]
            timestamp = entry["timestamp"]

            if not os.path.isfile(image_path):
                tqdm.write(f"⚠️ Warning: Image not found, skipping: {image_path}")
                continue

            tqdm.write(f"\n[{timestamp}] {os.path.basename(image_path)}")

            # BATCH CALL (single image still works but keeps model loaded)
            description = describe_batch(
                client,
                [image_path],   # still supports batching
                args.model,
                args.prompt
            )

            if description is None:
                continue

            line = f"{timestamp} - {description}"

            f.write(line + "\n")
            f.flush()

    tqdm.write(f"\n✅ Finished processing all frames. Saved to: {args.output_file}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Describe images via Ollama SDK.")

    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--ollama-url", default="http://localhost:11434")

    args = parser.parse_args()

    main(args)