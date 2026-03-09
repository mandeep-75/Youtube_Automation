import ollama
import argparse
import os
import re

OLLAMA_URL = "http://localhost:11434"

UNIFIED_PROMPT = """\
You are a professional YouTube Shorts scriptwriter specializing in high-retention, cinematic narration.

DATA SOURCES:
1. ORIGINAL DIALOGUE (if any):
{transcript_text}

2. VISUAL FRAME DESCRIPTIONS:
{vision_text}

INSTRUCTIONS:
- Create a dramatic, suspenseful, and emotionally engaging narrative suitable for a viral YouTube Shorts video.
- If dialogue is provided, treat it as the factual backbone of the story.
- Use the visual descriptions to add cinematic detail, atmosphere, tension, and emotional context.
- The FIRST sentence MUST start with: "This man", "This woman", or "This".
- Write in a storytelling style that builds curiosity and keeps viewers watching.
- Target length: 120–180 words, but a variation of ±20–30 words is acceptable if it improves storytelling flow.
- The narration must read naturally in under ~60 seconds.

OUTPUT FORMAT:
- Output ONLY the final narration script.
- Write it as ONE continuous paragraph.
- Do NOT include timestamps, scene labels, bullet points, or character names.

STRUCTURE GUIDELINE:
- Start with a strong hook.
- Build tension and curiosity in the middle.
- End with a powerful closing line, twist, or life lesson.

FINAL SCRIPT:
"""


def extract_fallback_script(thinking_text: str) -> str:
    markers = [
        "FINAL SCRIPT:", "NARRATION SCRIPT:", "Final Script:",
        "Draft:", "Script:", "Result:"
    ]

    for marker in markers:
        if marker in thinking_text:
            potential = thinking_text.split(marker)[-1].strip()
            if len(potential) > 50:
                return potential

    blocks = [b.strip() for b in re.split(r'\n\s*\n', thinking_text) if b.strip()]

    for block in reversed(blocks):
        if len(block) > 100:
            return block

    return ""


def generate_script(vision_text, transcript_text=None,
                    model="qwen3.5:9b", ollama_url=OLLAMA_URL):

    transcript_val = transcript_text.strip() if transcript_text else "[No audio script available]"

    prompt_content = UNIFIED_PROMPT.format(
        transcript_text=transcript_val,
        vision_text=vision_text.strip(),
    )

    client = ollama.Client(host=ollama_url)

    print(f"[step4_llm_script] Calling model {model}...")

    stream = client.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt_content}],
        think=False,        # Safe even if disabled
        stream=True,
        options={
            "num_ctx": 16384,
            "temperature": 0.7,
        }
    )

    accumulated_content = []
    accumulated_thinking = []
    in_thinking = False

    for chunk in stream:

        if not chunk:
            continue

        message = chunk.get("message")
        if not message:
            continue

        thinking = message.get("thinking", None)
        content = message.get("content", None)

        # ---- Thinking stream ----
        if thinking is not None:

            if not in_thinking:
                print("\n[THINKING]\n", end="", flush=True)
                in_thinking = True

            accumulated_thinking.append(thinking)
            print(thinking, end="", flush=True)
            continue

        # ---- Response stream ----
        if content is not None:

            if in_thinking:
                print("\n\n[RESPONSE]\n", end="", flush=True)
                in_thinking = False
            elif not accumulated_content:
                print("\n[RESPONSE]\n", end="", flush=True)

            accumulated_content.append(content)
            print(content, end="", flush=True)

    print("\n")

    final_script = "".join(accumulated_content).strip()
    final_thinking = "".join(accumulated_thinking).strip()

    if not final_script and final_thinking:
        print("[step4_llm_script] Extracting script from thinking...")
        final_script = extract_fallback_script(final_thinking)

    return final_script, final_thinking


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--transcript", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--ollama-url", default=OLLAMA_URL)

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        vision_data = f.read()

    transcript_data = None
    if args.transcript and os.path.isfile(args.transcript):
        with open(args.transcript, "r", encoding="utf-8") as f:
            transcript_data = f.read()

    script, thinking = generate_script(
        vision_data,
        transcript_data,
        model=args.model,
        ollama_url=args.ollama_url
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(script or "[Error: Model returned empty script]")

    print(f"[step4_llm_script] Script saved to {args.output}")

    if thinking:
        think_path = args.output.replace(".txt", ".thinking.txt")

        with open(think_path, "w", encoding="utf-8") as f:
            f.write(thinking)

        print(f"[step4_llm_script] Thinking saved to {think_path}")