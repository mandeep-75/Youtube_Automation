#!/usr/bin/env python3

import os
import json
import pickle
import argparse
import re
from pathlib import Path
import ollama

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# ===============================
# CONFIG
# ===============================

OLLAMA_MODEL = "jaahas/qwen3.5-uncensored:9b"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "youtube_token.pickle"

# ===============================
# PROMPT FOR METADATA
# ===============================

METADATA_PROMPT = """
You are a YouTube Shorts SEO expert.

Given this video script:

{script}

Create viral metadata:

RULES:
- Title under 90 characters
- Include #shorts
- Description 2 sentences max
- Include 3-5 hashtags
- 10 tags

Return JSON only in this format:
{{
"title": "...",
"description": "...",
"tags": ["tag1","tag2"]
}}
"""

# ===============================
# HELPERS
# ===============================

def extract_json(text):
    """Extract JSON from LLM response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found in LLM response")

def generate_metadata(script_text):
    """Generate YouTube metadata with Ollama, showing live thinking trace."""

    prompt = METADATA_PROMPT.format(script=script_text)

    print("💡 Ollama is thinking...")

    # Enable thinking and streaming
    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        think=True,       # enable thinking trace
        stream=True,
        options={"temperature": 0.8, "keep_alive": -1}
    )

    in_thinking = False
    response_text = ""

    for chunk in stream:
        # Each chunk may contain reasoning (thinking) or final content
        if getattr(chunk.message, "thinking", None) and not in_thinking:
            in_thinking = True
            print("🧠 Thinking Trace:\n", end="")

        if getattr(chunk.message, "thinking", None):
            print(chunk.message.thinking, end="", flush=True)

        elif getattr(chunk.message, "content", None):
            if in_thinking:
                print("\n\n✅ Final Metadata:\n", end="")
                in_thinking = False
            print(chunk.message.content, end="", flush=True)
            response_text += chunk.message.content

    print("\n")  # newline after streaming

    # Extract JSON from final content
    metadata = extract_json(response_text)
    return metadata

def get_authenticated_service():
    """Authenticate with YouTube and return API client."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

def upload_video(youtube, video_file, metadata):
    """Upload video to YouTube."""
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

    print("Uploading video...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload {int(status.progress() * 100)}%")

    print("✅ Upload complete")
    print("Video ID:", response["id"])

# ===============================
# MAIN
# ===============================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--script", required=True, help="Path to script.txt")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print("❌ Video file not found")
        return
    if not os.path.exists(args.script):
        print("❌ Script file not found")
        return

    # Read script
    with open(args.script, "r", encoding="utf-8") as f:
        script_text = f.read()

    # print("Generating metadata with Ollama...")
    # metadata = generate_metadata(script_text)
    # print(json.dumps(metadata, indent=2))

    print("Authenticating with YouTube...")
    youtube = get_authenticated_service()

    print("Uploading video...")
    upload_video(youtube, args.video, metadata)

if __name__ == "__main__":
    main()