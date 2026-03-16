#!/usr/bin/env python3
"""
ig_graph_api_worker.py
──────────────────────
Instagram Graph API (Official) uploader for Reels.

Uses resumable upload for direct video upload to Meta servers.
"""

import os
import sys
import time
import json
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(src_dir)
sys.path.insert(0, project_root)

from src import config


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = config.PROJECT_ROOT
IG_API_VERSION = config.IG_GRAPH_API_VERSION
ACCESS_TOKEN = config.IG_GRAPH_ACCESS_TOKEN
IG_USER_ID = config.IG_GRAPH_USER_ID

IG_GRAPH_API_URL = "https://graph.facebook.com"
IG_UPLOAD_HOST = "rupload.facebook.com"

METADATA_PROMPT = """
You are an Instagram Reels expert specializing in viral content optimization.

Given this video script:

{script}

Create a highly engaging Instagram Reels caption optimized for maximum reach and engagement.

CAPTION STRUCTURE (follow this exactly):

1. HOOK (first line - must stop the scroll):
   - Start with an intriguing question, bold statement, or trend-aligned opener
   - Examples: "Wait for this...", "POV:", "You need to see this...", "The secret most people miss..."
   - Keep it under 80 characters

2. BODY (2-3 short paragraphs with line breaks):
   - Tell a mini-story or provide value/context
   - Use conversational tone - like texting a friend
   - Include 1-2 emoji to break up text (🔥✨💯🤯📸🎬)
   - Add subtle pacing with line breaks

3. CTA (call to action - crucial for engagement):
   - Choose ONE: "Save for later 💾", "Share with a friend", "Comment your thoughts", "Follow for more"
   - Place before hashtags

4. HASHTAGS (strategic mix - 15-20 tags):
   - 3-5 popular hashtags (#viral #reels #trending #fyp #explore)
   - 5-8 niche hashtags (content-specific)
   - 3-5 ultra-niche hashtags (very specific to your micro-niche)
   - Example mix: #viral #reels #fyp #travel #travelgram #wanderlust #solotravel #travelingram #adventure #explore

OUTPUT FORMAT:
Return ONLY valid JSON with this structure:
{{
  "caption": "Your full caption with hook, line breaks, CTA, and hashtags",
  "cover_image_hint": "Brief note about which frame would work best as thumbnail (e.g., 'high contrast close-up', 'moment with text', 'outdoor landscape')"
}}

Important:
- Use double quotes for ALL strings in JSON
- Include actual line breaks (\\n) in caption for readability
- No explanatory text outside the JSON
- Make the CTA feel natural, not spammy
"""


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    text = text.strip()
    
    brace_count = 0
    start = -1
    for i, c in enumerate(text):
        if c == '{':
            if start == -1:
                start = i
            brace_count += 1
        elif c == '}':
            brace_count -= 1
            if brace_count == 0 and start != -1:
                content = text[start:i+1]
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass
                start = -1
    
    raise ValueError("No valid JSON found in LLM response")


def generate_metadata(script_text: str) -> dict:
    import ollama
    prompt = METADATA_PROMPT.format(script=script_text)
    print(f"\n💡 Generating Instagram caption with Ollama ({config.LLM_MODEL})...")

    client = ollama.Client(host=config.OLLAMA_URL)
    response = client.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response["message"]["content"].strip()
    print(f"\n[RESPONSE]\n{response_text[:500]}...")

    return extract_json(response_text)


# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM GRAPH API UPLOAD (RESUMABLE)
# ─────────────────────────────────────────────────────────────────────────────

def create_resumable_container(caption: str, video_duration: float = None) -> dict:
    """Create a resumable upload container for video"""
    url = f"{IG_GRAPH_API_URL}/{IG_API_VERSION}/{IG_USER_ID}/media"
    
    data = {
        "media_type": "REELS",
        "upload_type": "resumable",
        "caption": caption,
        "share_to_feed": True,
        "access_token": ACCESS_TOKEN
    }
    
    # Add video duration if known (helps Instagram process the video)
    if video_duration:
        data["video_length"] = video_duration
    
    print("   Creating resumable container...")
    response = requests.post(url, json=data)
    result = response.json()
    
    if "id" in result:
        print(f"   ✅ Container created: {result['id']}")
        return result
    else:
        raise Exception(f"Failed to create container: {result}")


def upload_video_to_meta(container_id: str, video_path: str) -> bool:
    """Upload video directly to Meta's servers using resumable upload"""
    file_size = os.path.getsize(video_path)
    
    upload_url = f"https://{IG_UPLOAD_HOST}/ig-api-upload/{IG_API_VERSION}/{container_id}"
    
    print(f"   Uploading video to Meta ({file_size:,} bytes)...")
    
    headers = {
        "Authorization": f"OAuth {ACCESS_TOKEN}",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Type": "application/octet-stream"
    }
    
    with open(video_path, "rb") as f:
        response = requests.post(upload_url, headers=headers, data=f, timeout=300)
    
    result = response.json()
    
    if result.get("success"):
        print("   ✅ Video uploaded successfully!")
        return True
    else:
        raise Exception(f"Video upload failed: {result}")


def check_media_status(container_id: str) -> dict:
    """Check if video is ready for publishing"""
    url = f"{IG_GRAPH_API_URL}/{IG_API_VERSION}/{container_id}"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "status_code,status"
    }
    
    response = requests.get(url, params=params)
    return response.json()


def publish_media(container_id: str) -> str:
    """Publish the media container"""
    url = f"{IG_GRAPH_API_URL}/{IG_API_VERSION}/{IG_USER_ID}/media_publish"
    
    data = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN
    }
    
    print("   Publishing media...")
    response = requests.post(url, json=data)
    result = response.json()
    
    if "id" in result:
        print(f"   ✅ Published! Media ID: {result['id']}")
        return result["id"]
    else:
        raise Exception(f"Failed to publish: {result}")


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe"""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError) as e:
        print(f"   ⚠️ Could not get video duration: {e}")
        return None


def upload_reel(video_path: str, caption: str) -> str:
    """Upload a Reel using Instagram Graph API with resumable upload"""
    
    # Get video duration for container
    video_duration = get_video_duration(video_path)
    if video_duration:
        print(f"   Video duration: {video_duration:.1f}s")
    
    # Step 1: Create resumable container
    container = create_resumable_container(caption, video_duration)
    container_id = container["id"]
    
    # Step 2: Upload video directly to Meta
    upload_video_to_meta(container_id, video_path)
    
    # Step 3: Wait for video processing
    print("   Waiting for video processing...")
    max_wait = 300  # 5 minutes
    wait_interval = 5
    elapsed = 0
    
    while elapsed < max_wait:
        status = check_media_status(container_id)
        status_code = status.get("status_code", "")
        
        print(f"   Status: {status_code} ({elapsed}s)")
        
        if status_code == "FINISHED":
            print("   ✅ Video processing complete!")
            break
        elif status_code == "ERROR":
            raise Exception(f"Video processing failed: {status}")
        elif status_code == "PUBLISHED":
            print("   ✅ Already published!")
            break
        
        time.sleep(wait_interval)
        elapsed += wait_interval
    
    if elapsed >= max_wait:
        raise Exception("Video processing timeout")
    
    # Step 4: Publish
    media_id = publish_media(container_id)
    
    return media_id


def check_api_limits():
    """Check current API rate limits"""
    url = f"{IG_GRAPH_API_URL}/{IG_API_VERSION}/{IG_USER_ID}/content_publishing_limit"
    params = {"access_token": ACCESS_TOKEN}
    
    response = requests.get(url, params=params)
    return response.json()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python ig_graph_api_worker.py <video_folder>")
        return 1

    folder = sys.argv[1]
    video = os.path.join(folder, "final_video.mp4")
    script = os.path.join(folder, "script.txt")

    # Validate inputs
    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        return 1
    if not os.path.exists(video):
        print(f"❌ final_video.mp4 missing in {folder}")
        return 1
    if not os.path.exists(script):
        print(f"❌ script.txt missing in {folder}")
        return 1
    if os.path.exists(os.path.join(folder, "ig_id.txt")):
        print("⚠️  Already uploaded (ig_id.txt exists). Skipping.")
        return 0

    # Check API credentials
    if not ACCESS_TOKEN:
        print("❌ Error: IG_GRAPH_ACCESS_TOKEN not set in .env")
        return 1

    if not IG_USER_ID:
        print("❌ Error: IG_GRAPH_USER_ID not set in .env")
        return 1

    # Read script
    print(f"\n📄 Reading script from {script}")
    with open(script, "r", encoding="utf-8") as f:
        script_text = f.read()

    # Generate metadata
    try:
        metadata = generate_metadata(script_text)
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        return 1

    # Check API limits
    try:
        limits = check_api_limits()
        print(f"\n📊 API Limits: {limits}")
    except Exception as e:
        print(f"⚠️ Could not check limits: {e}")

    # Upload
    try:
        print("\n🚀 Uploading Reel to Instagram (Official API)...")
        media_id = upload_reel(video, metadata.get("caption", ""))
        
        # Save media ID
        id_file = os.path.join(folder, "ig_id.txt")
        with open(id_file, "w") as f:
            f.write(media_id)
        
        print("\n✅ SUCCESS! Reel uploaded to Instagram")
        print(f"   Media ID: {media_id}")
        
        return 0
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())