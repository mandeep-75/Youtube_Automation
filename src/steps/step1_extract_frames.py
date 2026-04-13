import os
import sys
import argparse
import json
import cv2
from datetime import timedelta

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config

DEBUG_MODE = config.DEBUG_MODE
DEBUG_MAX_FRAMES = config.DEBUG_MAX_FRAMES


def extract_frames(video_path: str, interval_sec: float, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Error opening video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise Exception("Could not read FPS from video")

    frame_interval = max(int(fps * interval_sec), 1)
    entries = []
    frame_count = 0

    success, frame = cap.read()
    while success:
        if frame_count % frame_interval == 0:
            # Debug mode: stop after max frames
            if DEBUG_MODE and len(entries) >= DEBUG_MAX_FRAMES:
                print(
                    f"DEBUG: Stopping frame extraction at {DEBUG_MAX_FRAMES} frames (debug mode)"
                )
                break

            time_sec = frame_count / fps
            timestamp = str(timedelta(seconds=int(time_sec)))
            frame_filename = os.path.join(output_dir, f"frame_{frame_count:05d}.png")
            cv2.imwrite(frame_filename, frame)
            entries.append({"path": frame_filename, "timestamp": timestamp})
        success, frame = cap.read()
        frame_count += 1

    cap.release()

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    mode_str = " (debug mode)" if DEBUG_MODE else ""
    print(f"Extracted {len(entries)} frames to '{output_dir}'{mode_str}")
    print(f"Manifest saved to: {manifest_path}")
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-file", type=str, required=True)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--output-dir", type=str, default="outputs/frames")
    args = parser.parse_args()

    extract_frames(args.video_file, args.interval, args.output_dir)
