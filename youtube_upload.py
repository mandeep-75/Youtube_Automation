#!/usr/bin/env python3

import os
import json
import pickle
import re
import curses
from pathlib import Path
import ollama

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


# ===============================
# CONFIG
# ===============================

OUTPUT_DIR = "outputs"

OLLAMA_MODEL = "jaahas/qwen3.5-uncensored:9b"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "youtube_token.pickle"


# ===============================
# PROMPT
# ===============================

METADATA_PROMPT = """
You are a YouTube Shorts SEO expert.

Given this video script:

{script}

Create viral metadata.

RULES:
- Title under 90 characters
- Include #shorts
- Description 2 sentences max
- Include 3-5 hashtags
- 10 tags

Return JSON only:

{{
"title": "...",
"description": "...",
"tags": ["tag1","tag2"]
}}
"""


# ===============================
# VIDEO DISCOVERY
# ===============================

def get_videos():
    videos = []

    if not os.path.exists(OUTPUT_DIR):
        return videos

    for name in sorted(os.listdir(OUTPUT_DIR)):
        folder = os.path.join(OUTPUT_DIR, name)

        if os.path.isdir(folder):
            video = os.path.join(folder, "final_video.mp4")

            if os.path.exists(video):
                videos.append(name)

    return videos


# ===============================
# TUI
# ===============================

def draw_menu(stdscr, selected, videos):
    stdscr.clear()

    stdscr.addstr(1, 2, "┌──────────────────────────────────┐")
    stdscr.addstr(2, 2, "│       Select Video to Upload     │")

    for i, video in enumerate(videos):
        prefix = "▶ " if i == selected else "  "
        line = f"{prefix}{video}"
        stdscr.addstr(3 + i, 2, "│ " + line.ljust(32) + " │")

    stdscr.addstr(3 + len(videos), 2, "└──────────────────────────────────┘")

    stdscr.refresh()


def menu(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)

    videos = get_videos()

    if not videos:
        stdscr.addstr(2, 2, "No videos found in outputs/")
        stdscr.getch()
        return None

    selected = 0

    while True:
        draw_menu(stdscr, selected, videos)

        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(videos)

        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(videos)

        elif key in [10, 13]:
            return videos[selected]


# ===============================
# LLM METADATA
# ===============================

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise ValueError("No JSON found in response")


def generate_metadata(script_text):

    prompt = METADATA_PROMPT.format(script=script_text)

    print("\n💡 Ollama thinking...\n")

    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        think=True,
        stream=True,
        options={"temperature": 0.8}
    )

    response_text = ""
    thinking = False

    for chunk in stream:

        if getattr(chunk.message, "thinking", None):
            if not thinking:
                print("🧠 Thinking:\n")
                thinking = True

            print(chunk.message.thinking, end="", flush=True)

        elif getattr(chunk.message, "content", None):

            if thinking:
                print("\n\n✅ Final Metadata:\n")
                thinking = False

            print(chunk.message.content, end="", flush=True)
            response_text += chunk.message.content

    print("\n")

    return extract_json(response_text)


# ===============================
# YOUTUBE AUTH
# ===============================

def get_authenticated_service():

    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


# ===============================
# UPLOAD
# ===============================

def upload_video(youtube, video_file, metadata):

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    print("\nUploading video...\n")

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            print(f"Upload {int(status.progress() * 100)}%")

    print("\n✅ Upload Complete")
    print("Video ID:", response["id"])


# ===============================
# MAIN
# ===============================

def main():

    selected = curses.wrapper(menu)

    if not selected:
        return

    folder = os.path.join(OUTPUT_DIR, selected)

    video = os.path.join(folder, "final_video.mp4")
    script = os.path.join(folder, "script.txt")

    print("\nSelected:", selected)

    if not os.path.exists(script):
        print("❌ script.txt missing")
        return

    with open(script, "r", encoding="utf-8") as f:
        script_text = f.read()

    print("\nGenerating metadata...\n")
    metadata = generate_metadata(script_text)

    print(json.dumps(metadata, indent=2))

    print("\nAuthenticating YouTube...")
    youtube = get_authenticated_service()

    upload_video(youtube, video, metadata)


if __name__ == "__main__":
    main()