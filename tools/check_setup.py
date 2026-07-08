#!/usr/bin/env python3
"""Check that the environment is ready for the pipeline."""

import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


def check(condition: bool, msg: str, icon: str = PASS) -> bool:
    print(f"  {icon}  {msg}")
    return condition


def run() -> int:
    errors = 0
    warnings = 0

    print(f"\n{'='*50}")
    print("  YouTube Automation — Setup Check")
    print(f"{'='*50}\n")

    print(" Python")
    print(f"{'─'*40}")
    py_version = sys.version_info
    check(py_version.major >= 3, f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")

    print("\n Virtual Environment")
    print(f"{'─'*40}")
    venv_python = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
    venv_exists = os.path.isfile(venv_python)
    check(venv_exists, ".venv/bin/python found")
    if not venv_exists:
        print("   Run: python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt")
        errors += 1

    print("\n Dependencies")
    print(f"{'─'*40}")
    deps = ["ollama", "cv2", "pysubs2", "faster_whisper", "PIL", "kittentts"]
    for dep in deps:
        try:
            __import__(dep)
            check(True, dep)
        except ImportError:
            check(False, dep)
            errors += 1

    print("\n FFmpeg")
    print(f"{'─'*40}")
    local_ffmpeg = os.path.join(PROJECT_ROOT, "tools", "ffmpeg")
    local_ffprobe = os.path.join(PROJECT_ROOT, "tools", "ffprobe")
    if os.path.isfile(local_ffmpeg):
        check(True, "tools/ffmpeg (local)")
    else:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            check(True, f"system ffmpeg: {system_ffmpeg}")
        else:
            check(False, "ffmpeg not found — run: brew install ffmpeg")
            errors += 1

    if os.path.isfile(local_ffprobe):
        check(True, "tools/ffprobe (local)")
    else:
        system_ffprobe = shutil.which("ffprobe")
        if system_ffprobe:
            check(True, "system ffprobe")
        else:
            check(False, "ffprobe not found")
            errors += 1

    print("\n Ollama")
    print(f"{'─'*40}")
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            models = [line.split()[0] for line in result.stdout.strip().split("\n")[1:] if line.strip()]
            check(True, f"Ollama running ({len(models)} models)")
            for model in ["qwen3.5:0.8b", "qwen3.5:9b"]:
                if model in models:
                    check(True, f"  {model}")
                else:
                    check(False, f"  {model} — run: ollama pull {model}", WARN)
                    warnings += 1
        else:
            check(False, "Ollama not responding", FAIL)
            errors += 1
    except FileNotFoundError:
        check(False, "Ollama not installed — run: brew install ollama", FAIL)
        errors += 1

    print("\n Configuration")
    print(f"{'─'*40}")

    print(f"\n{'='*50}")
    if errors == 0 and warnings == 0:
        print(f"  {PASS} Everything looks great!")
    elif errors == 0:
        print(f"  {WARN} {warnings} warning(s) — pipeline should still work")
    else:
        print(f"  {FAIL} {errors} error(s) — fix before running pipeline")
    print(f"{'='*50}\n")

    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(run())
