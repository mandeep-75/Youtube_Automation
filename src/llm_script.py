
import requests

YOUTUBE_SHORTS_PROMPT = """
Rewrite the following frame descriptions into a cinematic, high-retention YouTube Shorts script. Start with a powerful hook that begins with words like “This man…”, “Those men…”, “These women…” to immediately create tension or curiosity. Make the narration slightly dramatic and emotionally intense, but still believable. Exaggerate the stakes just enough to make it feel urgent and critical. Use vivid, immersive language as if narrating a suspenseful scene. Build tension continuously throughout the paragraph, keeping it as one flowing narrative—do not break into multiple paragraphs or include timestamps or scene labels. End with a strong, memorable line that leaves the viewer with a warning or life lesson. Keep the entire script short enough to be read in under 60 seconds.
Here are the frame descriptions to rewrite:
{vision_text}

"""

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"

import argparse

def generate_script(vision_text: str) -> str:
    prompt = YOUTUBE_SHORTS_PROMPT.format(vision_text=vision_text)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=60
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        print(f"Error calling LLM: {e}")
        # fallback to original text if LLM fails
        return vision_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    with open(args.input, "r") as f:
        descriptions = f.read()
    
    print(f"Generating script from {args.input}...")
    script = generate_script(descriptions)
    
    with open(args.output, "w") as f:
        f.write(script)
    print(f"Script saved to {args.output}")