import ollama
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src import config

OLLAMA_MODEL = config.LLM_MODEL
OLLAMA_URL = config.OLLAMA_URL

UNIFIED_PROMPT = """\
ROLE:
You are a viral YouTube Shorts scriptwriter who specializes in high-retention cinematic storytelling. Your narration should feel like a raw, intense friend telling an unbelievable story directly to the camera. The tone is edgy, dramatic, and emotionally gripping, but still YouTube-friendly and suitable for monetization.

DATA SOURCES:
1. VIDEO DURATION: {duration} seconds
2. TARGET WORD COUNT: ~{target_words} words can be longer or shorter by 10% of the target words (based on {wps} words/sec)
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

def generate_script(vision_text, transcript_text=None,
                    duration=0.0, wps=2.5,
                    model=None, ollama_url=None):

    transcript_val = transcript_text.strip() if transcript_text else "[No audio script available]"
    target_words = int(float(duration) * float(wps)) if float(duration) > 0 else 150

    effective_model = model if model else OLLAMA_MODEL
    effective_url = ollama_url if ollama_url else OLLAMA_URL

    prompt_content = UNIFIED_PROMPT.format(
        duration=duration,
        wps=wps,
        target_words=target_words,
        transcript_text=transcript_val,
        vision_text=vision_text.strip(),
    )

    print(f"[step4_llm_script] Calling Ollama model: {effective_model}...")
    
    client = ollama.Client(host=effective_url)
    
    # Stream the chat response to show live thinking output
    stream = client.chat(
        model=effective_model,
        messages=[{"role": "user", "content": prompt_content}],
        think=True,
        options={"num_predict": 4000, "num_ctx": 8192},
        keep_alive=0,
        stream=True,
    )
    
    response_text = []
    thinking_text = []
    in_thinking = False
    
    for chunk in stream:
        # Handle both object-based (standard SDK) and dict-based chunks
        if hasattr(chunk, 'message'):
            msg = chunk.message
            thought = getattr(msg, 'thinking', '') or ''
            content = getattr(msg, 'content', '') or ''
        else:
            msg = chunk.get('message', {})
            thought = msg.get('thinking', '') or ''
            content = msg.get('content', '') or ''

        # Both thinking and content can be in the same chunk
        if thought:
            if not in_thinking:
                print("\nThinking:\n", end="", flush=True)
                in_thinking = True
            print(thought, end="", flush=True)
            thinking_text.append(thought)
        
        if content:
            if in_thinking:
                print("\n\nAnswer:\n", end="", flush=True)
                in_thinking = False
            print(content, end="", flush=True)
            response_text.append(content)
    
    print()  # final newline
    final_script = "".join(response_text).strip()
    final_thinking = "".join(thinking_text).strip()
    
    if final_thinking:
        print(f"\n[THINKING]\n{final_thinking[:500]}...")
    
    if final_script:
        print(f"\n[RESPONSE]\n{final_script[:500]}...")
    
    return final_script, final_thinking


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--transcript", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--wps", type=float, default=2.5)
    parser.add_argument("--model", default=None)
    parser.add_argument("--ollama-url", default=None)

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
        ollama_url=args.ollama_url,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(script or "[Error: Model returned empty script]")

    print(f"[step4_llm_script] Script saved to {args.output}")

    if thinking:
        think_path = args.output.replace(".txt", ".thinking.txt")

        with open(think_path, "w", encoding="utf-8") as f:
            f.write(thinking)

        print(f"[step4_llm_script] Thinking saved to {think_path}")