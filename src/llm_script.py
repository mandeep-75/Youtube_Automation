
import requests

YOUTUBE_SHORTS_PROMPT = """
Rewrite the following mechanical frame descriptions into a cinematic, high-retention YouTube Shorts script.

Start with a powerful hook that immediately creates tension or curiosity.
Be slightly dramatic and emotionally intense, but keep it realistic.
Add sensory details (sound of metal, smell of grease, resistance of rust, tension in the hands).
Exaggerate the stakes slightly to make it feel urgent and important.
Use vivid, immersive language like you’re narrating a suspense scene.

Build tension throughout the paragraph.
Make the viewer feel like something could go wrong at any second.
Do NOT add timestamps.
Do NOT add scene labels.
Do NOT break into multiple paragraphs.
Write it as one continuous paragraph.
End with a strong, memorable line that feels like a warning or life lesson.
Keep it under 60 seconds of spoken narration.

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