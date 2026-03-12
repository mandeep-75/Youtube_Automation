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

from instagrapi import Client
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ===============================
# CONFIG
# ===============================

UPLOAD_QUEUE_DIR = os.path.join(PROJECT_ROOT, "upload_queue")
UPLOADED_DIR = os.path.join(PROJECT_ROOT, "uploaded")
OLLAMA_MODEL = "jaahas/qwen3.5-uncensored:9b"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = os.path.join(PROJECT_ROOT, "client_secret.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "youtube_token.pickle")
IG_SESSION_FILE = os.path.join(PROJECT_ROOT, "ig_session.json")

IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")

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

IG_METADATA_PROMPT = """
You are an Instagram Reels viral SEO expert.

Given this video script:

{script}

Create an engaging Instagram Reels caption.

RULES:
- Start with a catchy hook line
- Short engaging description (1-2 sentences)
- Include 5 to 10 relevant hashtags at the end
- Use a few emojis
- Return JSON only.

Return JSON only:

{{
  "caption": "Your generated caption here with #hashtags"
}}
"""


# ===============================
# VIDEO DISCOVERY
# ===============================

def get_videos():
    """Return list of video data from upload_queue and uploaded."""
    videos = []
    
    # Check both directories
    for parent in [UPLOAD_QUEUE_DIR, UPLOADED_DIR]:
        if not os.path.exists(parent):
            continue
            
        for name in sorted(os.listdir(parent)):
            folder = os.path.join(parent, name)
            if os.path.isdir(folder) and os.path.exists(os.path.join(folder, "final_video.mp4")):
                yt_done = os.path.exists(os.path.join(folder, "youtube_id.txt"))
                ig_done = os.path.exists(os.path.join(folder, "ig_id.txt"))
                
                # Check if this video name is already in the list (from another dir)
                # to avoid duplicates if someone manually copied folders
                if any(v["name"] == name for v in videos):
                    continue
                    
                videos.append({
                    "name": name,
                    "folder": folder,
                    "parent": parent,
                    "yt_done": yt_done,
                    "ig_done": ig_done
                })
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
            name = video_data["name"]
            yt_tag = "[YT]" if video_data["yt_done"] else "    "
            ig_tag = "[IG]" if video_data["ig_done"] else "    "
            
            y = 3 + i
            if y >= h - 4:
                safe_addstr(stdscr, y, 6, "... more videos ...")
                break

            status = f"{yt_tag} {ig_tag} {name}"
            if i == selected:
                safe_addstr(stdscr, y, 4, f"> {status}", curses.color_pair(1))
            else:
                safe_addstr(stdscr, y, 6, status)

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
            return videos[selected]
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
    print("\n💡 Ollama thinking (YouTube)...\n")
    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": 0.8}
    )
    response_text = ""
    for chunk in stream:
        if getattr(chunk.message, "content", None):
            print(chunk.message.content, end="", flush=True)
            response_text += chunk.message.content
    print("\n")
    return extract_json(response_text)


def generate_ig_metadata(script_text):
    prompt = IG_METADATA_PROMPT.format(script=script_text)
    print("\n💡 Ollama thinking (Instagram)...\n")
    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": 0.8}
    )
    response_text = ""
    for chunk in stream:
        if getattr(chunk.message, "content", None):
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
    print("\nUploading to YouTube...\n")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  YouTube {int(status.progress() * 100)}%")
            
    print("\n✅ YouTube Success:", response["id"])
    
    # Save video ID to log file in the folder
    folder_path = os.path.dirname(video_file)
    with open(os.path.join(folder_path, "youtube_id.txt"), "w") as f:
        f.write(response["id"])


# ===============================
# INSTAGRAM AUTH & UPLOAD
# ===============================

def get_authenticated_client_ig():
    cl = Client()
    if os.path.exists(IG_SESSION_FILE):
        cl.load_settings(IG_SESSION_FILE)
        try:
            cl.login(IG_USERNAME, IG_PASSWORD)
            return cl
        except Exception:
            pass
    print("🔑 Instagram login...")
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.dump_settings(IG_SESSION_FILE)
    return cl


def upload_video_ig(cl, video_file, metadata):
    caption = metadata.get("caption", "")
    print(f"\nUploading Reel: {caption[:50]}...\n")
    media = cl.clip_upload(path=video_file, caption=caption)
    print(f"✅ Instagram Success: https://www.instagram.com/reel/{media.code}")
    
    # Save PK to log file
    folder_path = os.path.dirname(video_file)
    with open(os.path.join(folder_path, "ig_id.txt"), "w") as f:
        f.write(str(media.pk))


# ===============================
# MAIN
# ===============================

def main(stdscr):
    selected_data = select_video(stdscr)
    if not selected_data:
        return

    name = selected_data["name"]
    folder = selected_data["folder"]
    video = os.path.join(folder, "final_video.mp4")
    script_path = os.path.join(folder, "script.txt")

    if not os.path.exists(script_path):
        h, w = stdscr.getmaxyx()
        safe_addstr(stdscr, h - 2, 2, f"X script.txt missing in {name}. Any key.")
        stdscr.getch()
        return

    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read()

    # Leave curses mode
    curses.endwin()

    # YouTube Upload
    if not selected_data["yt_done"]:
        print(f"\n📺 Processing YouTube for: {name}")
        try:
            metadata = generate_metadata(script_text)
            youtube = get_authenticated_service()
            upload_video(youtube, video, metadata)
        except Exception as e:
            print(f"❌ YouTube failed: {e}")
    else:
        print(f"\n✅ YouTube already done for: {name}")

    # Instagram Upload
    if not selected_data["ig_done"]:
        print(f"\n📸 Processing Instagram for: {name}")
        try:
            if not IG_USERNAME or not IG_PASSWORD:
                print("❌ IG_USERNAME/PASSWORD missing in .env")
            else:
                metadata_ig = generate_ig_metadata(script_text)
                cl = get_authenticated_client_ig()
                upload_video_ig(cl, video, metadata_ig)
        except Exception as e:
            print(f"❌ Instagram failed: {e}")
    else:
        print(f"\n✅ Instagram already done for: {name}")

    # Move folder to uploaded directory if both done
    folder_now = folder # could have changed if we moved it midway (not really in this flow)
    yt_now = os.path.exists(os.path.join(folder, "youtube_id.txt"))
    ig_now = os.path.exists(os.path.join(folder, "ig_id.txt"))

    if yt_now and ig_now and selected_data["parent"] == UPLOAD_QUEUE_DIR:
        print("\n🚀 Both platforms complete. Moving to uploaded/...")
        if not os.path.exists(UPLOADED_DIR):
            os.makedirs(UPLOADED_DIR)
        dest = os.path.join(UPLOADED_DIR, name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.move(folder, dest)
        print(f"📂 Done.")
    
    input("\nPress Enter to return...")


if __name__ == "__main__":
    curses.wrapper(main)