# extract_frames.py
# Purpose: Extract frames from a video using cv2 (OpenCV).
# Run this with the environment that has cv2 installed (e.g. chatterbox env).
# It saves frames as PNG images and timestamps to a JSON manifest file.
# The fastvlm_describe.py script then reads those files.

import os
import argparse
import json
import cv2
from datetime import timedelta


def extract_frames(video_path: str, interval_sec: float, output_dir: str) -> str:
    """
    Extracts frames from `video_path` every `interval_sec` seconds.
    Saves each frame as a numbered PNG inside `output_dir`.
    Returns the path to a JSON manifest with frame paths and timestamps.
    """
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
    saved_count = 0

    success, frame = cap.read()
    while success:
        if frame_count % frame_interval == 0:
            time_sec = frame_count / fps
            timestamp = str(timedelta(seconds=int(time_sec)))
            frame_filename = os.path.join(output_dir, f"frame_{saved_count:05d}.png")
            cv2.imwrite(frame_filename, frame)
            entries.append({"path": frame_filename, "timestamp": timestamp})
            saved_count += 1
        success, frame = cap.read()
        frame_count += 1

    cap.release()

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    print(f"Extracted {saved_count} frames to '{output_dir}'")
    print(f"Manifest saved to: {manifest_path}")
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract frames from a video using cv2 (run in the env that has OpenCV)."
    )
    parser.add_argument("--video-file", type=str, required=True, help="Path to the input video file.")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval in seconds between extracted frames.")
    parser.add_argument("--output-dir", type=str, default="outputs/frames", help="Directory to save extracted frames.")
    args = parser.parse_args()

    extract_frames(args.video_file, args.interval, args.output_dir)
