import os
import argparse
import json
import base64
import requests
from tqdm import tqdm

OLLAMA_URL = "http://localhost:11434/api/generate"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def describe_image(image_path, model, prompt, ollama_url):
    base64_image = encode_image(image_path)
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [base64_image],
        "stream": True
    }
    
    thinking_text = []
    response_text = []
    last_was_thinking = False

    try:
        response = requests.post(ollama_url, json=payload, timeout=120, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            
            # 1. Capture Thinking (if model supports it)
            thought = chunk.get("thinking", "")
            if thought:
                if not last_was_thinking:
                    print("\n    [Thinking] ", end="", flush=True)
                    last_was_thinking = True
                print(thought, end="", flush=True)
                thinking_text.append(thought)
            
            # 2. Capture Response
            token = chunk.get("response", "")
            if token:
                if last_was_thinking:
                    print("\n    [Result] ", end="", flush=True)
                    last_was_thinking = False
                response_text.append(token)
                
            if chunk.get("done"):
                break

        return "".join(response_text).strip()
    except Exception as e:
        return f"[Error: {e}]"

def main(args):
    with open(args.manifest, "r", encoding="utf-8") as f:
        entries = json.load(f)

    print(f"Loaded {len(entries)} frames from manifest: {args.manifest}")
    print(f"Using Ollama model: {args.model}")
    print(f"Ollama URL: {args.ollama_url}")

    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)

    with open(args.output_file, "w", encoding="utf-8") as f:
        for entry in tqdm(entries):
            image_path = entry["path"]
            timestamp  = entry["timestamp"]
            
            print(f"\n[{timestamp}] Processing {os.path.basename(image_path)}...")
            description = describe_image(image_path, args.model, args.prompt, args.ollama_url)
            
            line = f"{timestamp} - {description}"
            print(f"    → {description}", flush=True)
            
            f.write(line + "\n")
            f.flush()

    print(f"\nDone ✅ Output saved to {args.output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Ollama VL (qwen2-vl etc.) on extracted frames.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--ollama-url", default="http://localhost:11434/api/generate")
    
    main(parser.parse_args())
