#!/usr/bin/env python3

import argparse
import subprocess
import tempfile
import logging
import os
from pathlib import Path
from typing import List, Dict
import pysubs2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subtitle-burner")


def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


class SubtitleBurner:

    def __init__(
        self,
        input_video: Path,
        subtitle_file: Path,
        output_video: Path,
        font_name: str,
        font_size: int,
        font_color: str,
        highlight_color: str,
        border_color: str,
        border_width: int,
        max_words: int,
    ):
        if not input_video.exists():
            raise FileNotFoundError(input_video)

        if not subtitle_file.exists():
            raise FileNotFoundError(subtitle_file)

        self.input_video = input_video
        self.subtitle_file = subtitle_file
        self.output_video = output_video
        self.font_name = font_name
        self.font_size = font_size
        self.font_color = font_color
        self.highlight_color = highlight_color
        self.border_color = border_color
        self.border_width = border_width
        self.max_words = max_words

        project_root = Path(__file__).parent.parent
        ffmpeg_path = project_root / "tools" / "ffmpeg"

        if not ffmpeg_path.exists():
            raise RuntimeError("FFmpeg not found in tools/ folder")

        self.ffmpeg = str(ffmpeg_path)

    def _load_word_segments(self) -> List[Dict]:
        subs = pysubs2.load(self.subtitle_file)
        words = []

        for line in subs:
            text = line.plaintext.strip()
            if not text:
                continue

            word_list = text.replace("\n", " ").split()
            duration = (line.end - line.start) / 1000
            per_word = duration / max(len(word_list), 1)

            for i, w in enumerate(word_list):
                words.append({
                    "start": line.start / 1000 + i * per_word,
                    "end": line.start / 1000 + (i + 1) * per_word,
                    "text": w
                })

        return words

    def _generate_ass(self) -> Path:
        words = self._load_word_segments()

        if not words:
            raise RuntimeError("No subtitle words found.")

        ass = pysubs2.SSAFile()

        style = pysubs2.SSAStyle()
        style.fontname = self.font_name
        style.fontsize = self.font_size

        r, g, b = hex_to_rgb(self.font_color)
        style.primary_color = pysubs2.Color(r, g, b)

        r, g, b = hex_to_rgb(self.highlight_color)
        style.secondary_color = pysubs2.Color(r, g, b)

        r, g, b = hex_to_rgb(self.border_color)
        style.outline_color = pysubs2.Color(r, g, b)

        style.outline = self.border_width
        style.shadow = 0
        style.alignment = 5
        style.marginv = 0

        ass.styles["Default"] = style

        # Convert hex to ASS format (&HBBGGRR&)
        def hex_to_ass(h):
            r_val, g_val, b_val = hex_to_rgb(h)
            return f"&H{b_val:02X}{g_val:02X}{r_val:02X}&"

        ass_font_color = hex_to_ass(self.font_color)
        ass_highlight_color = hex_to_ass(self.highlight_color)

        lines = []
        current = []

        for w in words:
            current.append(w)
            if len(current) >= self.max_words:
                lines.append(current)
                current = []

        if current:
            lines.append(current)

        for line in lines:
            for i, active_word in enumerate(line):
                start = int(active_word["start"] * 1000)
                end = int(active_word["end"] * 1000)

                text_parts = []
                for j, w in enumerate(line):
                    if i == j:
                        part = "{\\c" + ass_highlight_color + "}" + w["text"] + "{\\r}"
                    else:
                        part = "{\\c" + ass_font_color + "}" + w["text"]

                    text_parts.append(part)

                full_text = " ".join(text_parts)
                ass.events.append(pysubs2.SSAEvent(start=start, end=end, text=full_text))

        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        ass_path = output_dir / "subtitles.ass"

        ass.save(str(ass_path))

        logger.info(f"ASS created: {ass_path}")
        return ass_path

    def burn(self):
        logger.info("Hard burn mode")
        ass_file = self._generate_ass()

        try:
            cmd = [
                self.ffmpeg, "-y",
                "-i", str(self.input_video),
                "-vf", f"subtitles='{ass_file}'",
                "-c:a", "copy",
                str(self.output_video)
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"Done: {self.output_video}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed with exit code {e.returncode}: {e.stderr}")
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_video")
    parser.add_argument("subtitle_file")
    parser.add_argument("-o", "--output", default="output.mp4")
    parser.add_argument("--font-name",       default="Arial")
    parser.add_argument("--font-size",        type=int, default=12)
    parser.add_argument("--font-color",       default="#FFFFFF")
    parser.add_argument("--highlight-color",  default="#FFFF00")
    parser.add_argument("--border-color",     default="#000000")
    parser.add_argument("--border-width",     type=int, default=0)
    parser.add_argument("--max-words",        type=int, default=1)
    args = parser.parse_args()

    SubtitleBurner(
        Path(args.input_video),
        Path(args.subtitle_file),
        Path(args.output),
        args.font_name,
        args.font_size,
        args.font_color,
        args.highlight_color,
        args.border_color,
        args.border_width,
        args.max_words,
    ).burn()


if __name__ == "__main__":
    main()