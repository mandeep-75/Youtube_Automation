#!/usr/bin/env python3
"""
Burn subtitles into video files using FFmpeg and pysubs2.

Supports multiple subtitle formats (SRT, ASS, VTT, etc.) and provides
styling options for customizing subtitle appearance.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

try:
    import pysubs2
except ImportError:
    print("Error: pysubs2 is required. Install it with: pip install pysubs2")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("burn_subtitles.log"),
    ],
)
logger = logging.getLogger(__name__)


class SubtitleBurner:
    """Burn subtitles into video files."""

    def __init__(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: Optional[str] = None,
        font_name: str = "Arial",
        font_size: int = 24,
        font_color: str = "FFFFFF",
        border_color: str = "000000",
        border_width: int = 1,
        background_color: str = "000000",
        background_alpha: float = 0.8,
        ffmpeg_preset: str = "fast",
    ):
        """
        Initialize the SubtitleBurner.

        Args:
            video_path: Path to the input video file
            subtitle_path: Path to the subtitle file (SRT, ASS, VTT, etc.)
            output_path: Path for the output video file (auto-generated if not provided)
            font_name: Font name for subtitles
            font_size: Font size for subtitles
            font_color: Font color in hex (e.g., "FFFFFF" for white)
            border_color: Border color in hex
            border_width: Border width in pixels
            background_color: Background color in hex
            background_alpha: Background alpha (0.0 to 1.0)
            ffmpeg_preset: FFmpeg encoding preset (ultrafast, fast, medium, slow)
        """
        self.video_path = Path(video_path)
        self.subtitle_path = Path(subtitle_path)
        self.ffmpeg_preset = ffmpeg_preset

        # always prefer the bundled ffmpeg in tools/ if available
        bundled = Path(__file__).parent.parent / "tools" / "ffmpeg"
        self.ffmpeg_path = str(bundled) if bundled.exists() and bundled.stat().st_size > 0 else "ffmpeg"
        self.ffprobe_path = str(bundled).replace("ffmpeg", "ffprobe") if bundled.exists() else "ffprobe"

        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not self.subtitle_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

        if output_path:
            self.output_path = Path(output_path)
        else:
            stem = self.video_path.stem
            suffix = self.video_path.suffix
            self.output_path = self.video_path.parent / f"{stem}_subbed{suffix}"

        # Subtitle styling
        self.font_name = font_name
        self.font_size = font_size
        self.font_color = font_color  # Format: "BBGGRR" in hex for FFmpeg
        self.border_color = border_color
        self.border_width = border_width
        self.background_color = background_color
        self.background_alpha = background_alpha

        logger.info(f"Video: {self.video_path}")
        logger.info(f"Subtitles: {self.subtitle_path}")
        logger.info(f"Output: {self.output_path}")

    def _validate_ffmpeg(self) -> bool:
        """Check that the chosen ffmpeg binary exists and is executable."""
        if not shutil.which(self.ffmpeg_path):
            logger.error(f"FFmpeg not found at '{self.ffmpeg_path}'.")
            return False
        return True

    def _get_video_info(self) -> Optional[Tuple[int, int, float]]:
        """Get video width, height, and fps using ffprobe."""
        try:
            cmd = [
                self.ffprobe_path,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1:noesc=1",
                str(self.video_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split("\n")
            width = int(lines[0])
            height = int(lines[1])
            fps_str = lines[2]

            # Parse frame rate (e.g., "30000/1001" -> 29.97)
            if "/" in fps_str:
                num, denom = map(int, fps_str.split("/"))
                fps = num / denom
            else:
                fps = float(fps_str)

            logger.info(f"Video info - Width: {width}, Height: {height}, FPS: {fps:.2f}")
            return width, height, fps
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None

    def _convert_subtitle_format(self) -> Path:
        """
        Convert subtitle file to ASS format for better control with FFmpeg.
        Returns path to the converted ASS subtitle file.
        """
        try:
            subs = pysubs2.load(str(self.subtitle_path))

            # Apply styling
            for line in subs:
                line.style = "Default"

            # Create or update the Default style
            style = subs.styles["Default"]
            style.fontname = self.font_name
            style.fontsize = self.font_size
            style.primary_color = pysubs2.Color(*self._hex_to_bgr(self.font_color))
            style.outline_color = pysubs2.Color(
                *self._hex_to_bgr(self.border_color)
            )
            style.back_color = pysubs2.Color(
                *self._hex_to_bgr(self.background_color)
            )
            style.outline = self.border_width
            style.shadow = 0
            style.bold = False
            style.italic = False
            style.underline = False

            # Save to temporary ASS file
            temp_ass = tempfile.NamedTemporaryFile(
                suffix=".ass", delete=False
            ).name
            subs.save(temp_ass)
            logger.info(f"Converted subtitles to ASS format: {temp_ass}")
            return Path(temp_ass)
        except Exception as e:
            logger.error(f"Failed to convert subtitle format: {e}")
            raise

    def _hex_to_bgr(self, hex_color: str) -> Tuple[int, int, int]:
        """
        Convert hex color to BGR tuple.
        pysubs2 uses BGR format (Blue, Green, Red).
        """
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (b, g, r)
        else:
            raise ValueError(f"Invalid hex color: {hex_color}")

    def burn(self, hard_burn: bool = True) -> bool:
        """
        Burn subtitles into the video.

        Args:
            hard_burn: If True, permanently encode subtitles into video (slower).
                      If False, use softsub (faster but subtitles can be disabled).

        Returns:
            True if successful, False otherwise.
        """
        if not self._validate_ffmpeg():
            return False

        # Convert subtitles to ASS format with styling
        ass_subtitle_path = self._convert_subtitle_format()

        try:
            if hard_burn:
                return self._hard_burn_subtitles(ass_subtitle_path)
            else:
                return self._soft_burn_subtitles(ass_subtitle_path)
        finally:
            # Clean up temporary ASS file
            try:
                os.unlink(ass_subtitle_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")

    def _escape_filter_path(self, path: Path) -> str:
        """Escape a file path for use inside an FFmpeg filter expression.

        When invoking ffmpeg with a list (no shell), quoting is not applied. The
        filter parser treats colon and comma as option delimiters, so they must
        be backslash‑escaped. Backslashes are converted to forward slashes for
        compatibility with ffmpeg's path handling. Single quotes rarely appear
        in filenames, but we escape them as well just in case.
        """
        s = str(path).replace("\\", "/")
        # escape characters that have special meaning in filter expressions
        s = s.replace(":", "\\:").replace(",", "\\,")
        s = s.replace("'", "\\'")
        # do NOT wrap the result in quotes; subprocess will pass it literally
        return s

    def _hard_burn_subtitles(self, ass_subtitle_path: Path) -> bool:
        """
        Permanently encode subtitles into video (using ffmpeg's subtitles filter).
        This is slower but ensures subtitles are always visible, and supports
        full ASS styling.
        """
        logger.info("Starting hard burn (permanent encoding)...")

        escaped_ass = self._escape_filter_path(ass_subtitle_path)
        # Use the subtitles filter with an explicit filename option. Without
        # the "filename=" prefix ffmpeg will try to treat the path as a
        # filter option name, which fails for absolute paths (leading slashes).
        cmd = [
            self.ffmpeg_path,
            "-i",
            str(self.video_path),
            "-vf",
            f"subtitles=filename={escaped_ass}",
            "-c:v",
            "libx264",
            "-preset",
            self.ffmpeg_preset,
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-y",
            str(self.output_path),
        ]

        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True)
            if result.returncode == 0:
                logger.info(f"✓ Subtitles burned successfully: {self.output_path}")
                return True
            else:
                logger.error(f"FFmpeg returned exit code: {result.returncode}")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during subtitle burning: {e}")
            return False

    def _soft_burn_subtitles(self, ass_subtitle_path: Path) -> bool:
        """
        Embed subtitles as soft subs (not encoded into video).
        The video player can toggle subtitles on/off. Much faster than hard burn.
        """
        logger.info("Starting soft burn (embedded subtitles)...")

        cmd = [
            "ffmpeg",
            "-i",
            str(self.video_path),
            "-i",
            str(ass_subtitle_path),
            "-c:v",
            "libx264",
            "-preset",
            self.ffmpeg_preset,
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-c:s",
            "ass",
            "-y",
            str(self.output_path),
        ]

        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True)
            if result.returncode == 0:
                logger.info(f"✓ Subtitles embedded successfully: {self.output_path}")
                return True
            else:
                logger.error(f"FFmpeg returned exit code: {result.returncode}")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during subtitle embedding: {e}")
            return False


def main():
    """Command-line interface for burning subtitles."""
    parser = argparse.ArgumentParser(
        description="Burn subtitles into video files using FFmpeg and pysubs2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Hard burn subtitles (permanent encoding)
  python burn_subtitles.py input.mp4 input.srt

  # Soft subtitles with custom output
  python burn_subtitles.py input.mp4 input.srt -o output.mp4 --soft

  # Custom styling
  python burn_subtitles.py input.mp4 input.srt \\
    --font-name "DejaVu Sans" \\
    --font-size 28 \\
    --font-color "FFFFFF" \\
    --border-color "000000" \\
    --border-width 2

  # Fast encoding (lower quality)
  python burn_subtitles.py input.mp4 input.srt --preset ultrafast

  # Slow encoding (higher quality)
  python burn_subtitles.py input.mp4 input.srt --preset slow
        """,
    )

    parser.add_argument("video", help="Input video file")
    parser.add_argument("subtitle", help="Input subtitle file (SRT, ASS, VTT, etc.)")
    parser.add_argument(
        "-o",
        "--output",
        help="Output video file (auto-generated if not provided)",
    )
    parser.add_argument(
        "--soft",
        action="store_true",
        help="Embed subtitles as soft subs instead of hard burning",
    )
    parser.add_argument(
        "--font-name",
        default="Arial",
        help="Font name for subtitles (default: Arial)",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=24,
        help="Font size for subtitles (default: 24)",
    )
    parser.add_argument(
        "--font-color",
        default="FFFFFF",
        help="Font color in hex (default: FFFFFF - white)",
    )
    parser.add_argument(
        "--border-color",
        default="000000",
        help="Border color in hex (default: 000000 - black)",
    )
    parser.add_argument(
        "--border-width",
        type=int,
        default=1,
        help="Border width in pixels (default: 1)",
    )
    parser.add_argument(
        "--background-color",
        default="000000",
        help="Background color in hex (default: 000000 - black)",
    )
    parser.add_argument(
        "--preset",
        choices=["ultrafast", "fast", "medium", "slow", "slower"],
        default="fast",
        help="FFmpeg encoding preset (default: fast)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        burner = SubtitleBurner(
            video_path=args.video,
            subtitle_path=args.subtitle,
            output_path=args.output,
            font_name=args.font_name,
            font_size=args.font_size,
            font_color=args.font_color,
            border_color=args.border_color,
            border_width=args.border_width,
            background_color=args.background_color,
            ffmpeg_preset=args.preset,
        )

        success = burner.burn(hard_burn=not args.soft)

        if success:
            logger.info("✓ Subtitle burning completed successfully!")
            return 0
        else:
            logger.error("✗ Subtitle burning failed!")
            return 1

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
