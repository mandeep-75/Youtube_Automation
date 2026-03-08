import os
import argparse
import json
import ollama
from tqdm import tqdm

def describe_image(image_path, model, prompt, ollama_url):
    """
    Sends a single image to Ollama for description via official SDK.
    """
    if not os.path.isfile(image_path):
        tqdm.write(f"⚠️ Warning: Image not found, skipping: {image_path}")
        return None

    try:
        # Clean the URL to be a host only
        base_host = ollama_url.split("/api")[0] if "/api" in ollama_url else ollama_url
        client = ollama.Client(host=base_host)
        
        # We use generate for vision tasks with a single prompt and image
        stream = client.generate(
            model=model,
            prompt=prompt,
            images=[image_path],
            stream=True,
            think=True
        )

        response_text = []
        in_thinking = False

        for chunk in stream:
            # SDK maps 'thinking' field if model supports reasoning
            thought = getattr(chunk, 'thinking', '')
            if thought:
                if not in_thinking:
                    tqdm.write('Thinking:\n', end='')
                    in_thinking = True
                tqdm.write(thought, end="")
            
            # Content of the response
            token = getattr(chunk, 'response', '')
            if token:
                if in_thinking:
                    tqdm.write('\n\nAnswer:\n', end='')
                    in_thinking = False
                response_text.append(token)
                tqdm.write(token, end="")

        return "".join(response_text).strip()
    except Exception as e:
        return f"[Error: {e}]"

def main(args):
    with open(args.manifest, "r", encoding="utf-8") as f:
        entries = json.load(f)

    tqdm.write(f"\n🚀 Starting Vision: {len(entries)} frames")
    tqdm.write(f"🤖 Model: {args.model}")

    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)

    with open(args.output_file, "w", encoding="utf-8") as f:
        for entry in tqdm(entries, desc="Describing Frames"):
            image_path = entry["path"]
            timestamp  = entry["timestamp"]
            
            tqdm.write(f"\n[{timestamp}] {os.path.basename(image_path)}")
            description = describe_image(image_path, args.model, args.prompt, args.ollama_url)
            
            if description is None:
                continue # Skip entry if file was missing
                
            line = f"{timestamp} - {description}"
            tqdm.write(f"    → {description}")
            
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
    parser.add_argument("--batch-size", type=int, default=1, help="Legacy argument (ignored)")
    
    main(parser.parse_args())
