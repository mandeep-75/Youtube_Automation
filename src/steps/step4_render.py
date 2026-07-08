import os
import sys
import gc
import random
import shutil
import subprocess
import tempfile

from faster_whisper import WhisperModel  # type: ignore[import-untyped]

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_FFMPEG = os.path.join(_PROJECT_ROOT, "tools", "ffmpeg")
if not (os.path.isfile(_FFMPEG) and os.access(_FFMPEG, os.X_OK)):
    try:
        import imageio_ffmpeg  # type: ignore[import-untyped]
        _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        _FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_path() -> str:
    probe = _FFMPEG.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(probe):
        probe = shutil.which("ffprobe") or "ffprobe"
    return probe


def _duration(path: str) -> float:
    r = subprocess.run([_ffprobe_path(), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path],
                       capture_output=True, text=True, timeout=15)
    return float(r.stdout.strip())


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"[render] ffmpeg failed:\n{r.stderr}")


def _has_audio(path):
    try:
        r = subprocess.run([_ffprobe_path(), "-v", "error", "-select_streams", "a",
                            "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                           capture_output=True, text=True, timeout=15)
        return bool(r.stdout.strip())
    except Exception:
        return True


def merge_av(video_path: str, audio_path: str, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    vid_dur = _duration(video_path)
    aud_dur = _duration(audio_path)
    print(f"[render] video={vid_dur:.2f}s audio={aud_dur:.2f}s")

    tmp = tempfile.mkdtemp(prefix="render_av_")
    try:
        norm = os.path.join(tmp, "norm_audio.wav")
        if aud_dur < vid_dur:
            _run([_FFMPEG, "-y", "-i", audio_path, "-af",
                  f"apad=pad_dur={vid_dur - aud_dur}", "-t", str(vid_dur), norm])
        else:
            _run([_FFMPEG, "-y", "-i", audio_path, "-t", str(vid_dur), norm])

        print(f"[render] Muxing → {output_path}")
        _run([_FFMPEG, "-y", "-i", video_path, "-i", norm,
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
              "-shortest", output_path])
        return output_path
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def transcribe_subs(video_path: str, srt_path: str) -> str:
    if not _has_audio(video_path):
        print("[render] ⚠️ No audio – writing empty SRT")
        with open(srt_path, "w") as f:
            pass
        return srt_path

    tmp = tempfile.mkdtemp(prefix="render_subs_")
    wav = os.path.join(tmp, "audio.wav")
    try:
        _run([_FFMPEG, "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000",
              "-f", "wav", wav])
        model = WhisperModel(config.WHISPER_MODEL, device="auto",
                             compute_type=config.WHISPER_COMPUTE_TYPE)
        segments, info = model.transcribe(
            wav, language=config.WHISPER_LANG, beam_size=config.WHISPER_BEAM_SIZE,
            word_timestamps=True)
        words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    t = w.word.strip()
                    if t not in (".", ",", "!", "?"):
                        words.append({"start": w.start, "end": w.end, "text": t})
            else:
                t = seg.text.strip()
                if t:
                    words.append({"start": seg.start, "end": seg.end, "text": t})

        cleaned = []
        prev = None
        for w in words:
            if not w["text"]:
                continue
            if w["end"] - w["start"] > 2:
                continue
            if prev is not None and w["start"] - prev > 5:
                continue
            cleaned.append(w)
            prev = w["end"]

        lines = []
        for i, seg in enumerate(cleaned, 1):
            start = _fmt_srt(seg["start"])
            end = _fmt_srt(seg["end"])
            lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")

        os.makedirs(os.path.dirname(srt_path) or ".", exist_ok=True)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(lines))
        print(f"[render] SRT saved → {srt_path}")
        return srt_path
    finally:
        if 'model' in locals():
            del model
        shutil.rmtree(tmp, ignore_errors=True)
        gc.collect()


def _fmt_srt(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    h, millis = divmod(millis, 3600000)
    m, millis = divmod(millis, 60000)
    s, millis = divmod(millis, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def _video_dimensions(path: str) -> tuple[int, int]:
    r = subprocess.run([_ffprobe_path(), "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height",
                        "-of", "csv=s=x:p=0", path],
                       capture_output=True, text=True, timeout=15)
    parts = r.stdout.strip().split("x")
    return int(parts[0]), int(parts[1])


def burn_subs(video_path: str, srt_path: str, output_path: str) -> None:
    in_w, in_h = _video_dimensions(video_path)
    needs_portrait = in_w > in_h

    if needs_portrait:
        portrait_scale = config.PORTRAIT_WIDTH / in_w
        print(f"[render] Landscape → portrait (scale={portrait_scale:.3f})")
    else:
        portrait_scale = 1.0

    font = random.choice(config.SUBTITLE_FONTS) if isinstance(config.SUBTITLE_FONTS, list) else config.SUBTITLE_FONTS
    if isinstance(font, dict):
        font_name = str(font["name"])
        size_val = font.get("size", 36)
        font_size = float(size_val) if isinstance(size_val, (int, float)) else 36.0
    else:
        font_name = str(font)
        font_size = 36.0

    font_size *= portrait_scale
    print(f"[render] Font: {font_name} ({font_size:.1f})")
    import pysubs2
    subs = pysubs2.load(srt_path)
    ass = pysubs2.SSAFile()
    ass.info["PlayResX"] = str(config.PORTRAIT_WIDTH)
    ass.info["PlayResY"] = str(config.PORTRAIT_HEIGHT)

    style = pysubs2.SSAStyle()
    style.fontname = font_name
    style.fontsize = font_size
    scale = font_size / 120.0

    def _rgb(h):
        h = h.lstrip("#")
        return pysubs2.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    style.primarycolor = _rgb(config.SUBTITLE_FONT_COLOR)  # type: ignore[attr-defined]
    style.secondarycolor = _rgb(config.SUBTITLE_HIGHLIGHT_COLOR)  # type: ignore[attr-defined]
    style.outlinecolor = _rgb(config.SUBTITLE_OUTLINE_COLOR)  # type: ignore[attr-defined]
    style.outline = config.SUBTITLE_OUTLINE_WIDTH * scale
    style.shadow = 0
    style.bold = config.SUBTITLE_BOLD
    style.italic = config.SUBTITLE_ITALIC
    style.alignment = pysubs2.Alignment({"top": 8, "center": 5, "bottom": 2}.get(config.SUBTITLE_POSITION, 5))
    style.marginl = int(config.SUBTITLE_X_OFFSET * portrait_scale)
    style.marginr = int(config.SUBTITLE_X_OFFSET * portrait_scale)
    style.marginv = int(config.SUBTITLE_Y_OFFSET * portrait_scale)
    ass.styles["Default"] = style

    base = _ass_color(config.SUBTITLE_FONT_COLOR)
    highlight = _ass_color(config.SUBTITLE_HIGHLIGHT_COLOR)

    all_words: list[dict[str, str | int]] = []
    for line in subs:
        t = line.plaintext.strip()
        if t:
            all_words.append({"start": line.start, "end": line.end, "text": t})

    chunks = [all_words[i:i + config.SUBTITLE_MAX_WORDS] for i in range(0, len(all_words), config.SUBTITLE_MAX_WORDS)]
    for chunk in chunks:
        for i, cur in enumerate(chunk):
            parts = []
            for j, w in enumerate(chunk):
                if j == i:
                    parts.append("{\\c" + highlight + "}" + str(w["text"]) + "{\\r}")
                else:
                    parts.append("{\\c" + base + "}" + str(w["text"]))
            ass.events.append(
                pysubs2.SSAEvent(start=int(cur["start"]), end=int(cur["end"]), text=" ".join(parts))
            )

    ass_path = srt_path.replace(".srt", ".ass")
    ass.save(ass_path)

    pw = config.PORTRAIT_WIDTH
    ph = config.PORTRAIT_HEIGHT
    bg = config.PORTRAIT_BG_COLOR
    vf = (f"scale={pw}:{ph}:force_original_aspect_ratio=decrease,"
          f"pad={pw}:{ph}:(ow-iw)/2:(oh-ih)/2:color={bg},"
          f"subtitles='{ass_path}':fontsdir='{os.path.join(_PROJECT_ROOT, 'fonts')}'")
    _run([_FFMPEG, "-y", "-i", video_path,
          "-vf", vf,
          "-c:a", "copy", output_path])
    print(f"[render] Final → {output_path}")


def _ass_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    return f"&H{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}&"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    merged_root, merged_ext = os.path.splitext(args.output)
    merged = f"{merged_root}_merged{merged_ext}"
    merge_av(args.video, args.audio, merged)
    srt = os.path.splitext(merged)[0] + ".srt"
    transcribe_subs(merged, srt)
    burn_subs(merged, srt, args.output)
    for f in [merged, srt]:
        if os.path.exists(f):
            os.remove(f)
