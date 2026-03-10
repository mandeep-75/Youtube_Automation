#!/usr/bin/env python3

import os
import time
import shutil
import subprocess
from pathlib import Path

# --- CONFIG ---
WATCH_DIR = os.path.expanduser("~/Desktop/youtube_inbox")
PROCESSED_DIR = os.path.join(WATCH_DIR, "processed")
FAILED_DIR = os.path.join(WATCH_DIR, "failed")
POLL_INTERVAL = 5  # Seconds between scans
STABILITY_DELAY = 3  # Seconds to wait to ensure file is fully copied
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}

# Link to the main pipeline
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_SCRIPT = os.path.join(PROJECT_ROOT, "pipeline.py")
import sys
PYTHON_EXE = sys.executable # Use the same interpreter we are running on

def is_file_stable(filepath):
    """Check if the file size is stable (not being written)."""
    try:
        size1 = os.path.getsize(filepath)
        time.sleep(STABILITY_DELAY)
        size2 = os.path.getsize(filepath)
        return size1 == size2 and size1 > 0
    except OSError:
        return False

def process_video(video_path):
    print(f"\n🎬 New video detected: {os.path.basename(video_path)}")
    
    # Run the pipeline
    try:
        # We run the pipeline as a separate process
        subprocess.run([PYTHON_EXE, PIPELINE_SCRIPT, video_path], check=True, cwd=PROJECT_ROOT)
        
        # On success, move to processed
        dest = os.path.join(PROCESSED_DIR, os.path.basename(video_path))
        shutil.move(video_path, dest)
        print(f"✅ Successfully processed and moved to {PROCESSED_DIR}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Pipeline failed for {video_path}: {e}")
        dest = os.path.join(FAILED_DIR, os.path.basename(video_path))
        shutil.move(video_path, dest)
        print(f"⚠️ Moved to {FAILED_DIR}")
    except Exception as e:
        print(f"⚠️ Error: {e}")

def main():
    # Ensure dirs exist
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(FAILED_DIR, exist_ok=True)
    
    print(f"👀 Watching folder: {WATCH_DIR}")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            # Scan for new files
            files = [f for f in os.listdir(WATCH_DIR) 
                     if os.path.isfile(os.path.join(WATCH_DIR, f)) 
                     and Path(f).suffix.lower() in SUPPORTED_EXTENSIONS]
            
            for filename in files:
                filepath = os.path.join(WATCH_DIR, filename)
                
                # Check if it's a hidden file
                if filename.startswith("."):
                    continue
                
                if is_file_stable(filepath):
                    process_video(filepath)
                else:
                    print(f"⏳ Waiting for file stability: {filename}")
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping watcher...")

if __name__ == "__main__":
    main()
