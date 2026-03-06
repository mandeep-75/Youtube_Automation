import requests
import argparse
import os

OLLAMA_URL = "http://localhost:11434/api/generate"

FRAMES_ONLY_PROMPT = """\
Rewrite the following frame descriptions into a cinematic, high-retention YouTube Shorts narration script.
Start with a powerful hook that begins with phrases like "This man...", "Those men...", "This person...", "These people...", or "This moment..." to immediately create curiosity and tension.
The narration should feel dramatic, suspenseful, and emotionally intense, like a storyteller describing a shocking moment. Focus on actions, emotions, danger, and unfolding events, rather than naming specific objects or items that might appear in the scene.
Explain what seems to be happening in a way that is clear, vivid, and engaging. Slightly exaggerate the stakes so the moment feels urgent and meaningful.
Use immersive, cinematic language. The script must be one continuous paragraph, with no timestamps, scene labels, bullet points, or line breaks.
End with a strong, memorable closing line that leaves the viewer with a warning, realization, or life lesson.
The entire narration should be short enough to be read in under 60 seconds (approximately 120-150 words).

FRAME DESCRIPTIONS:
{vision_text}
"""

COMBINED_PROMPT = """\
You are a professional YouTube Shorts scriptwriter who specialises in high-retention, cinematic narration.

You have two sources of information about a video:

1. ORIGINAL DIALOGUE (what was actually said in the video, with timestamps):
{transcript_text}

2. VISUAL FRAME DESCRIPTIONS (what the AI vision model saw in each frame):
{vision_text}

Using BOTH sources:
- Let the original dialogue anchor you to what is really happening in the video.
- Use the frame descriptions to add vivid visual detail and atmosphere.
- Prioritise accurate story facts from the dialogue; use frames for colour and drama.

Write a single, continuous narration paragraph (no timestamps, no bullet points, no scene labels).
- Open with a powerful hook: "This man...", "These people...", "This moment...", or similar.
- Build tension steadily. Keep the tone dramatic, suspenseful, emotionally intense.
- Translate any specific technical objects or jargon into plain, universal language.
- End with a strong closing line — a warning, a realisation, or a life lesson.
- Target length: 120-150 words (readable in under 60 seconds).

Return ONLY the narration script. No preamble, no explanation.
"""


def generate_script(vision_text: str, transcript_text: str | None = None,
                    model: str = "qwen3.5:9b") -> str:
    if transcript_text and transcript_text.strip():
        print("[step4_llm_script] Mode: frames + transcript (combined)")
        prompt = COMBINED_PROMPT.format(
            transcript_text=transcript_text.strip(),
            vision_text=vision_text.strip(),
        )
    else:
        print("[step4_llm_script] Mode: frames only")
        prompt = FRAMES_ONLY_PROMPT.format(vision_text=vision_text.strip())

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        print(f"[step4_llm_script] Error calling LLM: {e}")
        return vision_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",      required=True)
    parser.add_argument("--transcript", default=None)
    parser.add_argument("--output",     required=True)
    parser.add_argument("--model",      default="qwen3.5:9b")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        vision_text = f.read()

    transcript_text = None
    if args.transcript and os.path.isfile(args.transcript):
        with open(args.transcript, "r", encoding="utf-8") as f:
            transcript_text = f.read()
        print(f"[step4_llm_script] Loaded transcript: {args.transcript}")
    else:
        print("[step4_llm_script] No transcript — frames-only mode.")

    print(f"[step4_llm_script] Generating script ...")
    script = generate_script(vision_text, transcript_text, model=args.model)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"[step4_llm_script] Script saved to {args.output}")