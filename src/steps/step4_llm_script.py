import ollama
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src import config

OLLAMA_MODEL = config.LLM_MODEL
OLLAMA_URL = config.OLLAMA_URL

UNIFIED_PROMPT = """You are a songwriter creating lyrics for a modern ambient-pop song with soft female vocals.

MUSIC STYLE:
{music_style}

INPUT DATA

VIDEO DURATION: {duration} seconds
TARGET WORD COUNT: {target_words} words

VISUAL SEQUENCE (chronological frame descriptions):
{vision_text}

ORIGINAL DIALOGUE (optional):
{transcript_text}

OUTPUT FORMAT

Return lyrics with these section markers:
[Verse]
(line 1)
(line 2)
...

[Pre-Chorus]
(line 1)
...

[Chorus]
(line 1)
...

[Bridge]
(line 1)
...

WRITING RULES

• Each line: 6-10 words
• Each section: 4-8 lines
• Match the visual narrative to lyrical storytelling
• Soft, dreamy, atmospheric tone
• Use markers: [Verse], [Pre-Chorus], [Chorus], [Bridge]
• Do not use bullet points or numbers
• Do not include explanations or notes
• Focus on mood, imagery, and emotional flow

TONE & STYLE

• Dreamy and atmospheric
• Soft female vocal friendly
• Ambient and uplifting
• Match the music style: {music_style}

LENGTH

Target word count: {target_words} words.
Do not exceed this length.
"""


def generate_script(
    vision_text,
    transcript_text=None,
    duration=0.0,
    wps=2.5,
    music_style=None,
    model=None,
    ollama_url=None,
):

    transcript_val = (
        transcript_text.strip() if transcript_text else "[No audio script available]"
    )
    target_words = int(float(duration) * float(wps))
    effective_music_style = music_style if music_style else config.MUSIC_STYLE

    effective_model = model if model else OLLAMA_MODEL
    effective_url = ollama_url if ollama_url else OLLAMA_URL

    prompt_content = UNIFIED_PROMPT.format(
        duration=duration,
        wps=wps,
        target_words=target_words,
        transcript_text=transcript_val,
        vision_text=vision_text.strip(),
        music_style=effective_music_style,
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
        if hasattr(chunk, "message"):
            msg = chunk.message
            thought = getattr(msg, "thinking", "") or ""
            content = getattr(msg, "content", "") or ""
        else:
            msg = chunk.get("message", {})
            thought = msg.get("thinking", "") or ""
            content = msg.get("content", "") or ""

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
    parser.add_argument("--music-style", default=None)
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
        music_style=args.music_style,
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
