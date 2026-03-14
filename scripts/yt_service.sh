#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# autoupload_daily.sh
# Automated daily YouTube upload scheduler.
#
# HOW TO USE:
#   1. Drop a folder into upload_queue/ (must have final_video.mp4 + script.txt)
#   2. This script runs automatically on boot and every 24 hours.
#   3. After upload, the folder is moved to uploaded/ ONLY IF Instagram is also done.
#
# Called by launchd (LaunchAgent) — safe to call repeatedly.
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$BASE_DIR")"

PYTHON="$PARENT_DIR/.venv/bin/python"
UPLOADER="$PARENT_DIR/src/uploaders/yt_worker.py"
QUEUE="$PARENT_DIR/upload_queue"
UPLOADED="$PARENT_DIR/uploaded"
LOG="$PARENT_DIR/yt_last_upload.txt"

TODAY=$(date +%F)

echo "──────────────────────────────────────"
echo "  YouTube Auto-Uploader  [$TODAY]"
echo "──────────────────────────────────────"

# ── Sanity checks ──────────────────────────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo "❌ Uploader venv not found: $PYTHON"
    echo "   Run setup_all_venvs.sh first."
    exit 1
fi

if [ ! -f "$UPLOADER" ]; then
    echo "❌ Uploader script not found: $UPLOADER"
    exit 1
fi

# ── Ensure folders exist ───────────────────────────────────────────────────
mkdir -p "$QUEUE"
mkdir -p "$UPLOADED"

# ── One-upload-per-day guard ───────────────────────────────────────────────
if [ -f "$LOG" ]; then
    LAST=$(cat "$LOG")
    if [ "$LAST" = "$TODAY" ]; then
        echo "✅ Already uploaded to YouTube today ($TODAY). Skipping."
        exit 0
    fi
fi

# ── Find oldest un-uploaded folder in upload_queue/ OR uploaded/ ──────────
CHOSEN=""

# 1. Check upload_queue/ first
for full in "$QUEUE"/*; do
    if [ ! -d "$full" ]; then continue; fi
    if [ -f "$full/final_video.mp4" ] && [ -f "$full/script.txt" ] && [ ! -f "$full/youtube_id.txt" ]; then
        CHOSEN="$full"
        break
    fi
done

# 2. If nothing in queue, check uploaded/ (in case IG script moved it early)
if [ -z "$CHOSEN" ]; then
    for full in "$UPLOADED"/*; do
        if [ ! -d "$full" ]; then continue; fi
        if [ -f "$full/final_video.mp4" ] && [ -f "$full/script.txt" ] && [ ! -f "$full/youtube_id.txt" ]; then
            CHOSEN="$full"
            break
        fi
    done
fi

if [ -z "$CHOSEN" ]; then
    echo "ℹ️  No videos waiting for YouTube upload."
    exit 0
fi

echo "📹 Found: $(basename "$CHOSEN")"
echo "🚀 Uploading to YouTube..."

"$PYTHON" "$UPLOADER" "$CHOSEN"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    NAME=$(basename "$CHOSEN")
    echo "$TODAY" > "$LOG"

    # ── Check if we should move the folder ─────────────────────────────────
    if [[ "$CHOSEN" == "$QUEUE"* ]]; then
        if [ -f "$CHOSEN/ig_id.txt" ]; then
            echo "ℹ️  Instagram upload is also complete. Moving to uploaded/"
            mv "$CHOSEN" "$UPLOADED/$NAME"
            echo "✅ Done! Moved → uploaded/$NAME"
        else
            echo "ℹ️  Instagram upload pending. Keeping in upload_queue/ for now."
        fi
    fi
    echo "📅 Log updated → $TODAY"
else
    echo "❌ YouTube upload failed (exit $EXIT_CODE)."
    exit $EXIT_CODE
fi