#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path
import pysubs2


"""
SUPPORTED FONTS (commonly available)

Windows / Cross platform:
- Arial
- Impact
- Verdana
- Tahoma
- Trebuchet MS

YouTube / TikTok style fonts:
- Montserrat
- Bebas Neue
- Poppins
- Anton
- Oswald

Example usage:
--font-name "Montserrat"
"""


def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def hex_to_ass(hex_color: str):
    r, g, b = hex_to_rgb(hex_color)
    return f"&H{b:02X}{g:02X}{r:02X}&"


def get_video_resolution(video_path, ffmpeg_bin):
    ffprobe = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w, h = map(int, result.stdout.strip().split("x"))
        return w, h
    except Exception:
        return None, None


class SubtitleBurner:

    def __init__(
        self,
        input_video,
        subtitle_file,
        output_video,
        font_name,
        font_size,
        font_color,
        highlight_color,
        outline_color,
        outline_width,
        position,
        max_words=1,
        bold=True,
        italic=False,
    ):

        self.input_video = Path(input_video)
        self.subtitle_file = Path(subtitle_file)
        self.output_video = Path(output_video)

        self.font_name = font_name
        self.font_size = font_size
        self.font_color = font_color
        self.highlight_color = highlight_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.position = position
        self.max_words = max_words
        self.bold = bold
        self.italic = italic

        project_root = Path(__file__).parent.parent
        ffmpeg_path = project_root / "tools" / "ffmpeg"

        if not ffmpeg_path.exists():
            raise RuntimeError("FFmpeg not found in tools/ folder")

        self.ffmpeg = str(ffmpeg_path)

    def generate_ass(self):

        subs = pysubs2.load(self.subtitle_file)

        ass = pysubs2.SSAFile()

        # Set resolution to match video for consistent font scaling
        width, height = get_video_resolution(self.input_video, self.ffmpeg)
        if width and height:
            ass.info["PlayResX"] = width
            ass.info["PlayResY"] = height
            # Scale font size based on height if it feels too small/large
            # Default libass assumes 384x288. If we set 1080p, font size 20 might be tiny.
            # However, setting PlayRes tells libass EXACTLY what coords to use.
        else:
            print("⚠️ Could not detect video resolution. Scaling might be off.")

        style = pysubs2.SSAStyle()

        style.fontname = self.font_name
        style.fontsize = self.font_size

        r, g, b = hex_to_rgb(self.font_color)
        style.primary_color = pysubs2.Color(r, g, b)

        r, g, b = hex_to_rgb(self.highlight_color)
        style.secondary_color = pysubs2.Color(r, g, b)

        r, g, b = hex_to_rgb(self.outline_color)
        style.outline_color = pysubs2.Color(r, g, b)

        style.outline = self.outline_width
        style.shadow = 0
        style.bold = self.bold
        style.italic = self.italic

        # positioning
        if self.position == "center":
            style.alignment = 5
        elif self.position == "bottom":
            style.alignment = 2
        else:
            style.alignment = 8

        style.marginv = 40

        ass.styles["Default"] = style

        base_color = hex_to_ass(self.font_color)
        highlight = hex_to_ass(self.highlight_color)

        # Extract all words with their timings
        all_words = []
        for line in subs:
            # We use plaintext to get rid of any existing tags for the highlighting logic
            text = line.plaintext.strip()
            if not text:
                continue
            all_words.append({
                "start": line.start,
                "end": line.end,
                "text": text
            })

        if not all_words:
            print("⚠️ No words found in subtitles.")
        else:
            # Word-by-word highlighting logic with sliding window
            for i, current_word in enumerate(all_words):
                # Calculate window: try to keep current word in focus
                # For max_words=1, it's just the current word.
                # For max_words > 1, we show a window.
                
                half_window = self.max_words // 2
                start_idx = max(0, i - half_window)
                end_idx = min(len(all_words), start_idx + self.max_words)
                
                # Adjust if we're near the end
                if end_idx - start_idx < self.max_words:
                    start_idx = max(0, end_idx - self.max_words)

                text_parts = []
                for j in range(start_idx, end_idx):
                    w = all_words[j]
                    if j == i:
                        # Highlight current word
                        text_parts.append("{\\c" + highlight + "}" + w["text"] + "{\\r}")
                    else:
                        # Use base color for others
                        text_parts.append("{\\c" + base_color + "}" + w["text"])

                full_text = " ".join(text_parts)
                
                ass.events.append(
                    pysubs2.SSAEvent(
                        start=current_word["start"],
                        end=current_word["end"],
                        text=full_text
                    )
                )

        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        ass_path = output_dir / "styled_subs.ass"

        ass.save(ass_path)

        return ass_path

    def burn(self):

        ass_file = self.generate_ass()

        cmd = [
            self.ffmpeg,
            "-y",
            "-i", str(self.input_video),
            "-vf", f"subtitles='{ass_file}'",
            "-c:a", "copy",
            str(self.output_video)
        ]

        subprocess.run(cmd, check=True)

        print("Finished:", self.output_video)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("input_video")
    parser.add_argument("subtitle_file")

    parser.add_argument("-o", "--output", default="output.mp4")

    parser.add_argument("--font-name", default="Montserrat Bold")
    parser.add_argument("--font-size", type=int, default=20)

    parser.add_argument("--font-color", default="#FFFFFF")
    parser.add_argument("--highlight-color", default="#FFFF00")

    parser.add_argument("--border-color", dest="outline_color", default="#000000")
    parser.add_argument("--border-width", dest="outline_width", type=float, default=2.0)
    
    parser.add_argument("--max-words", type=int, default=1)
    parser.add_argument("--bold", action="store_true", default=True)
    parser.add_argument("--no-bold", dest="bold", action="store_false")
    parser.add_argument("--italic", action="store_true", default=False)

    parser.add_argument(
        "--position",
        choices=["top", "center", "bottom"],
        default="center"
    )

    args = parser.parse_args()

    SubtitleBurner(
        args.input_video,
        args.subtitle_file,
        args.output,
        args.font_name,
        args.font_size,
        args.font_color,
        args.highlight_color,
        args.outline_color,
        args.outline_width,
        args.position,
        args.max_words,
        args.bold,
        args.italic
    ).burn()


if __name__ == "__main__":
    main()