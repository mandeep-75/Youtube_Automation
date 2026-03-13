import ollama
import argparse
import os
import re

OLLAMA_URL = "http://localhost:11434"

UNIFIED_PROMPT = """\
ROLE:
You are a viral YouTube Shorts scriptwriter who specializes in high-retention cinematic storytelling. Your narration should feel like a raw, intense friend telling an unbelievable story directly to the camera. The tone is edgy, dramatic, and emotionally gripping, but still YouTube-friendly and suitable for monetization.

DATA SOURCES:
1. VIDEO DURATION: {duration} seconds
2. TARGET WORD COUNT: ~{target_words} words (based on {wps} words/sec)
3. ORIGINAL DIALOGUE (if available): {transcript_text}
4. VISUAL FRAME DESCRIPTIONS: {vision_text}

IMPORTANT CONTEXT:
- The visual descriptions come from frames of one continuous video in chronological order.
- Reconstruct the scene as if you are watching the full video unfold in real time.
- Do NOT describe frames individually. Instead, combine them into a single flowing narrative.
- Use the dialogue (if provided) only when it strengthens the story.

TONE & STYLE:
- Voice should feel cinematic, intense, and conversational.
- Write like someone revealing a crazy real story late at night.
- Maintain high energy and curiosity throughout.
- Avoid offensive language or anything that could harm YouTube monetization.

STORY STRUCTURE:

1. Hook (first sentence):
- Must immediately stop the scroll.
- Must start with “This man…”, “This woman…”, or “This…”

2. Rising Tension:
- Connect visual clues to actions and emotions.
- Slowly reveal what is happening.

3. Escalation:
- Increase stakes or mystery.
- Make the viewer want to know what happens next.

4. Ending:
- Finish with a twist, shocking realization, lesson, or cliffhanger.

WRITING RULES:
- Write ONE continuous paragraph.
- No bullet points, timestamps, or labels.
- Do not repeat visual descriptions word-for-word.
- Focus on action, reaction, and tension.
- Keep the pacing fast and engaging for Shorts.

LENGTH & PACING:
- The script MUST be exactly sized for the video duration.
- Target word count: {target_words} words.
- Do NOT exceed this length, as the narration will be cut off.
- Ensure the pacing feels natural for the given duration.

OUTPUT FORMAT:
Return ONLY the final narration script as plain text.
Do not include explanations or formatting.
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
                    duration=0.0, wps=2.5,
                    model="qwen3.5:9b", ollama_url=OLLAMA_URL):

    transcript_val = transcript_text.strip() if transcript_text else "[No audio script available]"
    target_words = int(float(duration) * float(wps)) if float(duration) > 0 else 150

    prompt_content = UNIFIED_PROMPT.format(
        duration=duration,
        wps=wps,
        target_words=target_words,
        transcript_text=transcript_val,
        vision_text=vision_text.strip(),
    )

    client = ollama.Client(host=ollama_url)

    print(f"[step4_llm_script] Calling model {model}...")

    stream = client.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt_content}],
        think=False,       
        stream=True,
        keep_alive="5s",
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
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--wps", type=float, default=2.5)
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
        transcript_text=transcript_data,
        duration=args.duration,
        wps=args.wps,
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