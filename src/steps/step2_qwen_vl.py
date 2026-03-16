import os
import argparse
import json
import ollama
from tqdm import tqdm


def describe_frame(client, image_path, model, prompt, context_prompt: str = None):
    """
    Sends a single image to Ollama for description.
    Optionally includes context from previous frames.
    """

    final_prompt = context_prompt if context_prompt else prompt

    try:
        stream = client.generate(
            model=model,
            prompt=final_prompt,
            keep_alive="15s",
            images=[image_path],
            stream=True,
        )

        response_text = []
        in_thinking = False

        for chunk in stream:
            thought = chunk.get("thinking", "")
            if thought:
                if not in_thinking:
                    print("\nThinking:\n", end="", flush=True)
                    in_thinking = True
                print(thought, end="", flush=True)

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


def build_context_prompt(previous_frames: list, current_prompt: str) -> str:
    """
    Builds a prompt that includes context from previous frames.
    
    Args:
        previous_frames: List of (timestamp, description) tuples from earlier frames
        current_prompt: The base prompt for describing the current frame
    
    Returns:
        Enhanced prompt with previous frame context
    """
    if not previous_frames:
        return current_prompt
    
    context_lines = []
    for timestamp, desc in previous_frames:
        context_lines.append(f"[{timestamp}] {desc}")
    
    context_str = "\n".join(context_lines)
    
    enhanced_prompt = f"""Previous frames (for narrative continuity):
{context_str}

---

Current frame to describe:
[image]

Task: Describe this frame considering the narrative continuity from the previous frames above. 
- Note how the action progresses from previous scenes
- Maintain consistency with established visual elements
- Describe what's NEW or CHANGED from the previous frames

Base prompt:
{current_prompt}"""
    
    return enhanced_prompt


def main(args):

    with open(args.manifest, "r", encoding="utf-8") as f:
        entries = json.load(f)

    context_window = getattr(args, 'context_window', 5)
    
    tqdm.write(f"\n🚀 Starting Vision: {len(entries)} frames")
    tqdm.write(f"🤖 Model: {args.model}")
    tqdm.write(f"📚 Context window: {context_window} previous frames")

    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)

    base_host = args.ollama_url.split("/api")[0] if "/api" in args.ollama_url else args.ollama_url
    client = ollama.Client(host=base_host)

    previous_frames = []

    with open(args.output_file, "w", encoding="utf-8") as f:

        for entry in tqdm(entries, desc="Describing Frames"):

            image_path = entry["path"]
            timestamp = entry["timestamp"]

            if not os.path.isfile(image_path):
                tqdm.write(f"⚠️ Warning: Image not found, skipping: {image_path}")
                continue

            tqdm.write(f"\n[{timestamp}] {os.path.basename(image_path)}")

            context_prompt = None
            if previous_frames:
                context_prompt = build_context_prompt(
                    previous_frames[-context_window:],
                    args.prompt
                )

            description = describe_frame(
                client,
                image_path,
                args.model,
                args.prompt,
                context_prompt
            )

            if description is None:
                continue

            previous_frames.append((timestamp, description))

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
    parser.add_argument("--context-window", type=int, default=5,
                        help="Number of previous frames to include as context (default: 5)")

    args = parser.parse_args()

    main(args)
