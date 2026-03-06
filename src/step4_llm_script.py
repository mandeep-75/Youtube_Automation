import requests
import argparse
import json
import os

OLLAMA_URL = "http://localhost:11434/api/generate"

UNIFIED_PROMPT = """\
You are a professional YouTube Shorts scriptwriter who specialises in high-retention, cinematic narration.

DATA SOURCES:
1. ORIGINAL DIALOGUE (if any):
{transcript_text}

2. VISUAL FRAME DESCRIPTIONS (AI vision observations):
{vision_text}

INSTRUCTIONS:
- Use BOTH sources if available. If dialogue is present, use it as the anchor for the story's facts.
- Use visual descriptions to add atmosphere, tension, and vivid cinematic detail.
- If NO dialogue is provided, craft a compelling narrative purely from the visual action.
- Write a single, continuous narration paragraph (no timestamps, no bullet points, no scene labels).
- Open with a powerful hook: "This man...", "These people...", "This moment...", or similar.
- Build tension steadily. Keep the tone dramatic, suspenseful, and emotionally intense.
- Translate specific technical objects or jargon into plain, universal language.
- End with a strong closing line — a warning, a realisation, or a life lesson.
- Target length: 120-150 words (readable in under 60 seconds).

Return ONLY the narration script. No preamble, no explanation.
"""


def generate_script(vision_text: str, transcript_text: str | None = None,
                    model: str = "qwen3.5:9b", ollama_url: str = OLLAMA_URL) -> tuple[str, str]:
    
    transcript_val = transcript_text.strip() if transcript_text and transcript_text.strip() else "[No audio script available for this video]"
    
    print(f"[step4_llm_script] Generating script using unified prompt...")
    prompt = UNIFIED_PROMPT.format(
        transcript_text=transcript_val,
        vision_text=vision_text.strip(),
    )

    try:
        print()
        response = requests.post(
            ollama_url,
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True,
        )
        response.raise_for_status()

        thinking_text = []
        response_text = []
        
        last_was_thinking = False

        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            
            # 1. Native Thinking (for models like DeepSeek-R1, Qwen-Reasoning)
            thought = chunk.get("thinking", "")
            if thought:
                if not last_was_thinking:
                    print("\n--- Model is thinking ---\n", end="", flush=True)
                    last_was_thinking = True
                print(thought, end="", flush=True)
                thinking_text.append(thought)
            
            # 2. Final Response
            token = chunk.get("response", "")
            if token:
                if last_was_thinking:
                    print("\n\n--- Final Script ---\n", end="", flush=True)
                    last_was_thinking = False
                print(token, end="", flush=True)
                response_text.append(token)
                
            if chunk.get("done"):
                break

        print()
        
        final_script = "".join(response_text).strip()
        final_thinking = "".join(thinking_text).strip()
        
        # If the model didn't use native 'thinking' field but used <think> tags in response
        if not final_thinking and "<think>" in final_script:
            if "</think>" in final_script:
                parts = final_script.split("</think>")
                final_thinking = parts[0].replace("<think>", "").strip()
                final_script = parts[1].strip()
            
        return final_script, final_thinking

    except Exception as e:
        print(f"\n[step4_llm_script] Error calling LLM: {e}")
        return vision_text, ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",      required=True)
    parser.add_argument("--transcript", default=None)
    parser.add_argument("--output",     required=True)
    parser.add_argument("--model",      default="qwen3.5:9b")
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
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
    script, thinking = generate_script(vision_text, transcript_text, model=args.model, ollama_url=args.ollama_url)

    # Save final script
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"[step4_llm_script] Script saved to {args.output}")

    # Save thinking log if it exists
    if thinking:
        think_path = args.output.replace(".txt", ".thinking.txt")
        with open(think_path, "w", encoding="utf-8") as f:
            f.write(thinking)
        print(f"[step4_llm_script] Thinking log saved to {think_path}")