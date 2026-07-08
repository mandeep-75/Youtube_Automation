import os
import sys
import json
import cv2
import ollama
from datetime import timedelta
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


def extract_frames(video_path: str, interval_sec: float, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Error opening video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise Exception("Could not read FPS from video")

    frame_interval = max(int(fps * interval_sec), 1)
    entries: list[dict[str, str]] = []
    frame_count = 0

    success, frame = cap.read()
    while success:
        if frame_count % frame_interval == 0:
            if config.DEBUG_MODE and len(entries) >= config.DEBUG_MAX_FRAMES:
                print(f"DEBUG: Stopping at {config.DEBUG_MAX_FRAMES} frames")
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

    print(f"Extracted {len(entries)} frames to '{output_dir}'")
    return manifest_path


def describe_frames(manifest_path: str, output_file: str) -> None:
    with open(manifest_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    print(f"\n🚀 Vision: {len(entries)} frames with {config.VISION_MODEL}")
    client = ollama.Client(host=config.OLLAMA_URL)

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        for entry in tqdm(entries, desc="Describing Frames"):
            image_path = entry["path"]
            timestamp = entry["timestamp"]
            if not os.path.isfile(image_path):
                tqdm.write(f"⚠️ Image not found: {image_path}")
                continue
            try:
                stream = client.generate(
                    model=config.VISION_MODEL,
                    think=False,
                    prompt=config.VISION_PROMPT,
                    keep_alive="60s",
                    images=[image_path],
                    options={"num_ctx": 8192},
                    stream=True,
                )
                print(f"\n[{timestamp}]")
                response_text = []
                for chunk in stream:
                    token = chunk.get("response", "")
                    if token:
                        response_text.append(token)
                        print(token, end="", flush=True)
                print()
                description = "".join(response_text).strip()
            except Exception as e:
                description = f"[Error: {e}]"

            f.write(f"{timestamp} - {description}\n")
            f.flush()

    print(f"\n✅ Saved to: {output_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-file", required=True)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--frames-file", required=True)
    args = parser.parse_args()

    manifest = extract_frames(args.video_file, args.interval, args.output_dir)
    describe_frames(manifest, args.frames_file)
