import ollama
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src import config

OLLAMA_MODEL = config.LLM_MODEL
OLLAMA_URL = config.OLLAMA_URL

UNIFIED_PROMPT = """You are a viral YouTube Shorts scriptwriter who specializes in high-retention cinematic storytelling.

Your narration should feel like a friend telling an unbelievable real story directly to the camera late at night — intense, curious, and impossible to scroll past.

INPUT DATA

VIDEO DURATION: {duration} seconds
TARGET WORD COUNT: {target_words} words
AVERAGE SPEECH RATE: {wps} words per second

ORIGINAL DIALOGUE (optional):
{transcript_text}

VISUAL SEQUENCE (chronological frame descriptions):
{vision_text}

IMPORTANT CONTEXT

The visual descriptions represent frames from one continuous video in chronological order.

Do not mention frames or describe them individually.

Instead:
• Combine all visuals into one flowing narrative
• Infer actions, reactions, and emotions
• Tell the story naturally as events unfold

Use dialogue only if it strengthens the story.

TONE & STYLE

The voice should feel:
• Cinematic
• Conversational
• High-energy

Write using short, punchy sentences to maintain fast pacing.

The story must remain YouTube-friendly and advertiser safe.

Avoid:
• Profanity
• Hate speech
• Sexual content
• Political messaging

STORY STRUCTURE

Hook (first sentence)

The first sentence must immediately stop the scroll.

It must begin with one of these phrases:
"This man..."
"This woman..."
"This..."

Example style:
"This man thought he found something normal until it suddenly moved."

WRITING RULES

• Write one continuous paragraph
• Do not use bullet points in the script
• Do not add labels or timestamps
• Do not repeat the visual descriptions word-for-word
• Focus on action, reactions, and suspense
• Maintain fast pacing for Shorts

LENGTH & PACING

The script must match the video duration.

Target word count: {target_words} words.

Do not exceed this length.

OUTPUT FORMAT

Return only the final narration script as plain text.

Do not include explanations or formatting.
"""

def generate_script(vision_text, transcript_text=None,
                    duration=0.0, wps=2.5,
                    model=None, ollama_url=None):

    transcript_val = transcript_text.strip() if transcript_text else "[No audio script available]"
    target_words = int(float(duration) * float(wps))

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
        think=False,
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