#!/usr/bin/env python3

import os
import re
import sys
import time
import shutil
import subprocess
from pathlib import Path

# Link to the main pipeline
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- CONFIG ---
WATCH_DIR = os.path.join(PROJECT_ROOT, "yt_inbox")
OUTPUTS_DIR = os.path.join(WATCH_DIR, "outputs")  # outputs inside yt_inbox
PROCESSED_DIR = os.path.join(WATCH_DIR, "processed")
FAILED_DIR = os.path.join(WATCH_DIR, "failed")
POLL_INTERVAL = 5  # Seconds between scans
STABILITY_DELAY = 3  # Seconds to wait to ensure file is fully copied
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}

PIPELINE_SCRIPT = os.path.join(PROJECT_ROOT, "pipeline.py")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")
PYTHON_EXE = sys.executable  # Use the same interpreter we are running on
LOCK_FILE = os.path.join(PROJECT_ROOT, "watcher.lock")

def sanitize_filename(name):
    """Remove characters that are invalid in filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def is_file_stable(filepath):
    """Check if the file size is stable (not being written)."""
    try:
        size1 = os.path.getsize(filepath)
        time.sleep(STABILITY_DELAY)
        size2 = os.path.getsize(filepath)
        return size1 == size2 and size1 > 0
    except OSError:
        return False

def is_already_processed(video_path):
    """Check if video has already been processed (output exists in outputs/)."""
    video_name = os.path.basename(video_path)
    video_name = sanitize_filename(video_name)
    output_dir = os.path.join(OUTPUTS_DIR, video_name)
    
    # Check if output directory exists with final videos
    final_mixed = os.path.join(output_dir, "final_video_mixed.mp4")
    final_simple = os.path.join(output_dir, "final_video_simple.mp4")
    
    return os.path.exists(final_mixed) or os.path.exists(final_simple)

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

def acquire_lock():
    """Write our PID to lock file. Exit if another instance is already running."""
    if os.path.exists(LOCK_FILE):
        try:
            existing_pid = int(Path(LOCK_FILE).read_text().strip())
            # Check if that process is still alive
            os.kill(existing_pid, 0)
            print(f"❌ Watcher already running (PID {existing_pid}). Exiting.")
            sys.exit(1)
        except (ProcessLookupError, ValueError, PermissionError):
            pass  # Stale lock file (process ended) or no permission — safe to overwrite
    Path(LOCK_FILE).write_text(str(os.getpid()))

def release_lock():
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass

def main():
    acquire_lock()
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
                
                # Check if already processed - skip if output exists
                if is_already_processed(filepath):
                    print(f"⏭️  Already processed, skipping: {filename}")
                    # Move to processed folder
                    dest = os.path.join(PROCESSED_DIR, filename)
                    if not os.path.exists(dest):
                        shutil.move(filepath, dest)
                        print("   → Moved to processed/")
                    continue
                
                if is_file_stable(filepath):
                    process_video(filepath)
                else:
                    print(f"⏳ Waiting for file stability: {filename}")
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping watcher...")
    finally:
        release_lock()

if __name__ == "__main__":
    main()
