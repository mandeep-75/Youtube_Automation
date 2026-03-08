import ollama
import argparse
import os
import re

OLLAMA_URL = "http://localhost:11434"

# Enhanced prompt for better high-retention scriptwriting and clear output separation
UNIFIED_PROMPT = """\
You are a professional YouTube Shorts scriptwriter specializing in high-retention, cinematic narration.

DATA SOURCES:
1. ORIGINAL DIALOGUE (if any):
{transcript_text}

2. VISUAL FRAME DESCRIPTIONS:
{vision_text}

INSTRUCTIONS:
- Create a compelling narrative that feels dramatic, suspenseful, and emotionally intense.
- If dialogue is provided, use it as the anchor for the story's facts.
- Use visual descriptions to add atmosphere, tension, and vivid cinematic detail.
- Target length: 120-180 words (readable in under 60 seconds).
- OUTPUT FORMAT: Provide only the final narration script as ONE continuous paragraph.
- DO NOT include timestamps, scene labels, or character names.
- OPEN with a powerful hook and END with a strong closing line/life lesson.
- If you use a reasoning/thinking process, YOU MUST provide the final script after your thinking is complete.

FINAL SCRIPT:
"""


def extract_fallback_script(thinking_text: str) -> str:
    """
    If the model puts its final answer inside the thinking block, attempt to find it.
    Look for common markers or the last long paragraph.
    """
    # Look for common final markers
    markers = [
        "FINAL SCRIPT:", "NARRATION SCRIPT:", "Final Script:", "Final Draft:",
        "DRAFT 8:", "Draft:", "Script:", "Result:"
    ]
    for marker in markers:
        if marker in thinking_text:
            parts = thinking_text.split(marker)
            potential = parts[-1].strip()
            if len(potential) > 50: # Likely the script
                return potential

    # Fallback: Find the last continuous block of text that looks like a paragraph (no list numbers)
    stripped = thinking_text.strip()
    if not stripped:
        return ""
    
    # Split by double newlines or large breaks
    blocks = [b.strip() for b in re.split(r'\n\s*\n', stripped) if b.strip()]
    if blocks:
        # Check from end to find something that doesn't look like a numbered item or short label
        for block in reversed(blocks):
            if len(block) > 100 and not block.startswith(("1.", "2.", "Step", "Count", "Word")):
                return block
                
    return ""

def generate_script(vision_text: str, transcript_text: str | None = None,
                    model: str = "qwen3.5:9b", ollama_url: str = OLLAMA_URL) -> tuple[str, str]:
    
    # Clean up empty strings or placeholders
    transcript_val = transcript_text.strip() if transcript_text and transcript_text.strip() else "[No audio script available]"
    
    # Prepare the prompt
    prompt_content = UNIFIED_PROMPT.format(
        transcript_text=transcript_val,
        vision_text=vision_text.strip(),
    )

    try:
        # Initialize the official Ollama client
        # Note: ollama_url might be "http://localhost:11434/api/generate", 
        # but the SDK Client usually just takes the base host.
        base_host = ollama_url.split("/api")[0] if "/api" in ollama_url else ollama_url
        client = ollama.Client(host=base_host)
        
        print(f"[step4_llm_script] Calling model {model} via SDK...")
        
        stream = client.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt_content}],
            stream=True,
            think=False,
            options={
                "num_ctx": 16384,
                "temperature": 0.7,
            }
        )

        accumulated_content = []

        for chunk in stream:
            # Check for content field
            token = getattr(chunk.message, 'content', '')
            if token:
                accumulated_content.append(token)
                # print(token, end="", flush=True) # Optional: comment out for silent progress

        print("\n")
        
        final_script = "".join(accumulated_content).strip()
        final_thinking = "" # Since we disabled it
        
        # Handle models that use <think> tags inside the response field instead of the field
        if not final_thinking and "<think>" in final_script:
            if "</think>" in final_script:
                parts = final_script.split("</think>")
                final_thinking = parts[0].replace("<think>", "").strip()
                final_script = parts[1].strip()
            else:
                final_thinking = final_script.replace("<think>", "").strip()
                final_script = ""

        # FALLBACK: If final_script is empty but thinking is not, try to extract a script
        if not final_script and final_thinking:
            print("[step4_llm_script] Warning: Final script empty. Attempting to extract from thinking process...")
            extracted = extract_fallback_script(final_thinking)
            if extracted:
                print(f"[step4_llm_script] Extracted {len(extracted)} characters from thinking block.")
                final_script = extracted
            else:
                print("[step4_llm_script] Failed to extract clean script from thinking process.")

        return final_script, final_thinking

    except Exception as e:
        print(f"\n[step4_llm_script] Error calling Ollama SDK: {e}")
        return "", f"Error: {e}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",      required=True)
    parser.add_argument("--transcript", default=None)
    parser.add_argument("--output",     required=True)
    parser.add_argument("--model",      default="qwen3.5:9b")
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    args = parser.parse_args()

    # Load Vision Descriptions
    with open(args.input, "r", encoding="utf-8") as f:
        vision_data = f.read()

    # Load Transcript
    transcript_data = None
    if args.transcript and os.path.isfile(args.transcript):
        with open(args.transcript, "r", encoding="utf-8") as f:
            transcript_data = f.read()
        print(f"[step4_llm_script] Loaded transcript: {args.transcript}")

    # Generate
    script, thinking = generate_script(vision_data, transcript_data, model=args.model, ollama_url=args.ollama_url)

    # Save script
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(script or "[Error: Could not generate script from model response]")
    print(f"[step4_llm_script] Script saved to {args.output} ({len(script)} chars)")

    # Save thinking (if any)
    if thinking:
        think_path = args.output.replace(".txt", ".thinking.txt")
        with open(think_path, "w", encoding="utf-8") as f:
            f.write(thinking)
        print(f"[step4_llm_script] Thinking process log saved to {think_path}")