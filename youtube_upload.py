#!/usr/bin/env python3

import os
import json
import pickle
import re
import curses
import shutil
from pathlib import Path
import ollama

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


# ===============================
# CONFIG
# ===============================

UPLOAD_QUEUE_DIR = "upload_queue"
UPLOADED_DIR = "uploaded"
OLLAMA_MODEL = "jaahas/qwen3.5-uncensored:9b"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "youtube_token.pickle"

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
    """Return list of folder names that contain final_video.mp4."""
    videos = []
    if not os.path.exists(UPLOAD_QUEUE_DIR):
        return videos
    for name in sorted(os.listdir(UPLOAD_QUEUE_DIR)):
        folder = os.path.join(UPLOAD_QUEUE_DIR, name)
        if os.path.isdir(folder) and os.path.exists(os.path.join(folder, "final_video.mp4")):
            # Check if uploaded
            is_uploaded = os.path.exists(os.path.join(folder, "youtube_id.txt"))
            videos.append({"name": name, "uploaded": is_uploaded})
    return videos


# ===============================
# SELECTION MENU (CURSES)
# ===============================

def draw_border(window, y, x, height, width, title=""):
    """Draw a bordered box with optional title."""
    try:
        window.attron(curses.color_pair(2))
        window.border(0)
        if title:
            # Title is drawn on the top border (y=0)
            safe_addstr(window, 0, 2, f" {title} ")
        window.attroff(curses.color_pair(2))
    except curses.error:
        pass


def safe_addstr(window, y, x, text, attr=0):
    """Safely add a string to a curses window, handling bounds and potential ERR."""
    try:
        h, w = window.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        # Truncate to fit width
        max_len = w - x - 1
        if max_len <= 0:
            return
        window.addstr(y, x, text[:max_len], attr)
    except curses.error:
        pass


def select_video(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)   # selected item
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)  # borders
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK) # normal

    videos = get_videos()
    if not videos:
        safe_addstr(stdscr, 2, 2, "No videos found in upload_queue/")
        stdscr.refresh()
        stdscr.getch()
        return None

    selected = 0
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        if h < 8 or w < 40:
            safe_addstr(stdscr, 0, 0, "Terminal too small!")
            safe_addstr(stdscr, 1, 0, "Please enlarge window.")
            stdscr.refresh()
            key = stdscr.getch()
            if key == ord('q'): return None
            continue

        draw_border(stdscr, 0, 0, h - 1, w - 1, " Select Video to Upload ")

        for i, video_data in enumerate(videos):
            video = video_data["name"]
            uploaded = video_data["uploaded"]
            status_tag = " [OK]" if uploaded else ""
            
            y = 3 + i
            if y >= h - 4:
                safe_addstr(stdscr, y, 6, "... more videos ...")
                break

            if i == selected:
                safe_addstr(stdscr, y, 4, f"> {video}{status_tag}", curses.color_pair(1))
            else:
                safe_addstr(stdscr, y, 6, f"{video}{status_tag}")

        # Footer
        safe_addstr(stdscr, h - 3, 2, f"Total: {len(videos)}")
        footer_text = "[UP/DOWN or j/k] move  [Enter] select  [q] quit"
        safe_addstr(stdscr, h - 2, 2, footer_text)

        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            selected = (selected - 1) % len(videos)
        elif key in (curses.KEY_DOWN, ord('j')):
            selected = (selected + 1) % len(videos)
        elif key in (10, 13):
            return videos[selected]["name"]
        elif key == ord('q'):
            return None


# ===============================
# LLM METADATA
# ===============================

def extract_json(text):
    # Try to find the last occurrence of } to be safe if model adds junk
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            # Try to fix common trailing issues
            content = match.group(1)
            if content.count('{') > content.count('}'):
                content += '}' * (content.count('{') - content.count('}'))
            return json.loads(content)
    raise ValueError("No valid JSON found in response")


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
# YOUTUBE AUTH & UPLOAD
# ===============================

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Token refresh failed ({e}). Re-authenticating...")
                creds = None
        
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)


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
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    print("\nUploading video...\n")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload {int(status.progress() * 100)}%")
    print("\n✅ Upload Complete")
    print("Video ID:", response["id"])
    
    # Save video ID to log file in the folder
    folder_path = os.path.dirname(video_file)
    with open(os.path.join(folder_path, "youtube_id.txt"), "w") as f:
        f.write(response["id"])


# ===============================
# MAIN
# ===============================

def main(stdscr):
    selected = select_video(stdscr)
    if not selected:
        return

    folder = os.path.join(UPLOAD_QUEUE_DIR, selected)
    video = os.path.join(folder, "final_video.mp4")
    script = os.path.join(folder, "script.txt")

    if not os.path.exists(script):
        h, w = stdscr.getmaxyx()
        safe_addstr(stdscr, h - 2, 2, "X script.txt missing. Press any key.")
        stdscr.getch()
        return

    with open(script, "r", encoding="utf-8") as f:
        script_text = f.read()

    # Leave curses mode for metadata generation and upload
    curses.endwin()

    print("\nGenerating metadata...\n")
    try:
        metadata = generate_metadata(script_text)
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        input("Press Enter to exit...")
        return

    # Automatically upload without confirmation
    print("\nAuthenticating YouTube...")
    try:
        youtube = get_authenticated_service()
        if youtube:
            upload_video(youtube, video, metadata)
            
            # Move folder to uploaded directory
            if not os.path.exists(UPLOADED_DIR):
                os.makedirs(UPLOADED_DIR)
            dest_folder = os.path.join(UPLOADED_DIR, selected)
            # If destination already exists, remove it first or use a unique name
            if os.path.exists(dest_folder):
                shutil.rmtree(dest_folder)
            shutil.move(folder, dest_folder)
            print(f"\n📂 Moved '{selected}' to {UPLOADED_DIR}/")
            
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    curses.wrapper(main)