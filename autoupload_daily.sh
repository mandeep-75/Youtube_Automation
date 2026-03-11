#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# autoupload_daily.sh
# Automated daily YouTube upload scheduler.
#
# HOW TO USE:
#   1. Drop a folder into upload_queue/ (must have final_video.mp4 + script.txt)
#   2. This script runs automatically on boot and every 24 hours.
#   3. After upload, the folder is moved to uploaded/
#
# Called by launchd (LaunchAgent) — safe to call repeatedly.
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

PYTHON="$BASE_DIR/venvs/uploader/bin/python"
UPLOADER="$BASE_DIR/yt_bash_auto_upload.py"
QUEUE="$BASE_DIR/upload_queue"
UPLOADED="$BASE_DIR/uploaded"
LOG="$BASE_DIR/last_upload.txt"

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
        echo "✅ Already uploaded today ($TODAY). Skipping."
        exit 0
    fi
fi

# ── Find oldest un-uploaded folder in upload_queue/ ───────────────────────
CHOSEN=""
for full in "$QUEUE"/*; do
    # Skip README and non-directories
    if [ ! -d "$full" ]; then
        continue
    fi

    # Must have both required files
    if [ -f "$full/final_video.mp4" ] && [ -f "$full/script.txt" ]; then
        CHOSEN="$full"
        break
    fi
done

if [ -z "$CHOSEN" ]; then
    echo "ℹ️  No videos waiting in upload_queue/."
    echo "   Drop a folder with final_video.mp4 + script.txt into:"
    echo "   $QUEUE"
    exit 0
fi

echo "📹 Found: $(basename "$CHOSEN")"
echo "🚀 Uploading..."

"$PYTHON" "$UPLOADER" "$CHOSEN"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    # ── Move folder to uploaded/ ───────────────────────────────────────────
    NAME=$(basename "$CHOSEN")
    if [ -d "$CHOSEN" ]; then
        mv "$CHOSEN" "$UPLOADED/$NAME"
    fi
    echo "$TODAY" > "$LOG"
    echo ""
    echo "✅ Done! Moved → uploaded/$NAME"
    echo "📅 Log updated → $TODAY"
else
    echo "❌ Upload failed (exit $EXIT_CODE). Folder stays in upload_queue/."
    exit $EXIT_CODE
fi