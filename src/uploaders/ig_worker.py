#!/usr/bin/env python3
"""
ig_bash_auto_upload.py
──────────────────────
Automated Instagram Reels uploader.

Usage (called by a bash script or a bot):
    python ig_bash_auto_upload.py <video_folder>
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(src_dir)
sys.path.insert(0, project_root)

import json
import re
import ollama

from src import config


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG (from config.py)
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT        = config.PROJECT_ROOT
OLLAMA_MODEL        = config.LLM_MODEL
OLLAMA_URL          = config.OLLAMA_URL
IG_SESSION_FILE     = config.IG_SESSION_FILE
IG_USERNAME         = config.IG_USERNAME
IG_PASSWORD         = config.IG_PASSWORD


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG (from config.py)
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT        = config.PROJECT_ROOT
OLLAMA_MODEL        = config.LLM_MODEL
OLLAMA_URL          = config.OLLAMA_URL
IG_SESSION_FILE     = config.IG_SESSION_FILE
IG_USERNAME         = config.IG_USERNAME
IG_PASSWORD         = config.IG_PASSWORD

METADATA_PROMPT = """
Given this video script:

{script}

Create an engaging Instagram Reels caption with a hook and hashtags.

Respond with ONLY valid JSON:
{{"caption": "Your caption here with #hashtags"}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    # Find JSON block - look for first { and last }
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    
    if start == -1 or end == -1:
        raise ValueError("No JSON found in LLM response")
    
    content = text[start:end+1]
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Fix unquoted caption
    caption_match = re.search(r'"caption"\s*:\s*(.+)', content)
    if caption_match:
        caption_part = caption_match.group(1).strip()
        # If caption is unquoted, quote it
        if not (caption_part.startswith('"') and caption_part.endswith('"')):
            # Find the last } to close properly
            last_brace = caption_part.rfind('}')
            if last_brace > 0:
                caption = caption_part[:last_brace].strip().rstrip(',')
                if not caption.endswith('"'):
                    caption += '"'
                content = '{"caption": ' + caption + '}'
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

def generate_metadata(script_text: str) -> dict:
    prompt = METADATA_PROMPT.format(script=script_text)
    print(f"\n💡 Generating Instagram caption with Ollama ({OLLAMA_MODEL})...\n")

    client = ollama.Client(host=OLLAMA_URL)
    
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        options={"num_predict": 500}
    )
    
    response_text = response["message"]["content"].strip()
    thinking = response["message"].get("thinking", "") or ""
    
    if thinking:
        print(f"\n[THINKING]\n{thinking[:500]}...")
    
    print(f"\n[RESPONSE]\n{response_text[:500]}...")
    
    return extract_json(response_text)

# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM AUTH & UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def get_authenticated_client():
    """Use Playwright to get cookies, then login with instagrapi"""
    from playwright.sync_api import sync_playwright
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    print("🔑 Opening Instagram to get session...")
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    
    # Check if already logged in via cookies
    if "login" not in page.url.lower():
        print("✅ Already logged in - saving session")
        cookies = context.cookies()
        with open(IG_SESSION_FILE, "w") as f:
            json.dump(cookies, f)
        browser.close()
        playwright.stop()
    else:
        print("🔐 Logging in...")
        
        for sel in ['input[name="username"]', 'input[type="text"]']:
            try:
                page.wait_for_selector(sel, timeout=5000)
                page.fill(sel, IG_USERNAME)
                break
            except:
                continue
        
        for sel in ['input[name="password"]', 'input[type="password"]']:
            try:
                page.fill(sel, IG_PASSWORD)
                break
            except:
                continue
        
        page.click('button[type="submit"]')
        page.wait_for_timeout(5000)
        
        if "challenge" in page.url.lower():
            raise Exception("Instagram verification required")
        
        cookies = context.cookies()
        with open(IG_SESSION_FILE, "w") as f:
            json.dump(cookies, f)
        print("✅ Session saved")
        browser.close()
        playwright.stop()
    
    # Now use instagrapi with session
    from instagrapi import Client
    cl = Client()
    
    if os.path.exists(IG_SESSION_FILE) and os.path.getsize(IG_SESSION_FILE) > 0:
        try:
            cl.load_settings(IG_SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            print("✅ Instagram logged in via saved session")
            return cl
        except Exception as e:
            print(f"⚠️ Session login failed: {e}")
    
    # Direct login as fallback
    print("🔐 Direct login to Instagram...")
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.dump_settings(IG_SESSION_FILE)
    print("✅ Login successful")
    return cl


def upload_video(cl, video_file: str, metadata: dict) -> str:
    caption = metadata.get("caption", "Default caption")
    print(f"\n🚀 Uploading Reel to Instagram...")
    print(f"   Caption: {caption[:50]}...")
    
    media = cl.clip_upload(path=video_file, caption=caption)
    video_pk = media.pk
    video_code = media.code
    
    print(f"\n✅ Upload complete → https://www.instagram.com/reel/{video_code}/")
    return str(video_pk)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python ig_bash_auto_upload.py <video_folder>")
        return 1

    folder = sys.argv[1]
    video  = os.path.join(folder, "final_video.mp4")
    script = os.path.join(folder, "script.txt")

    # ── Validate inputs ────────────────────────────────────────────────────
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
        print(f"⚠️  Already uploaded (ig_id.txt exists). Skipping.")
        return 0

    if not IG_USERNAME or not IG_PASSWORD:
        print("❌ Error: IG_USERNAME and IG_PASSWORD environment variables are not set.")
        print("   Set them via Export, or edit this script directly.")
        return 1

    # ── Read script ────────────────────────────────────────────────────────
    print(f"\n📄 Reading script from {script}")
    with open(script, "r", encoding="utf-8") as f:
        script_text = f.read()

    # ── Generate metadata ──────────────────────────────────────────────────
    try:
        metadata = generate_metadata(script_text)
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        return 1

    # ── Authenticate & upload ──────────────────────────────────────────────
    print("\n🔑 Authenticating with Instagram (using browser)...")
    try:
        client = get_authenticated_client()
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return 1

    try:
        video_id = upload_video(client, video, metadata)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return 1

    # ── Mark as uploaded ───────────────────────────────────────────────────
    id_file = os.path.join(folder, "ig_id.txt")
    with open(id_file, "w") as f:
        f.write(video_id)
    print(f"📝 Instagram PK saved → {id_file}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
