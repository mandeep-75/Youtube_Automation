#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# auto_service.sh
# Auto-uploader service using separate uploaders for each platform.
#
# HOW TO USE:
#   1. Drop a folder into upload_queue/ (must have final_video_mixed.mp4,
#      final_video_simple.mp4, and script.txt)
#   2. This script runs automatically on boot and every 24 hours.
#   3. After all enabled platform uploads complete, folder is moved to uploaded/
#
# Called by launchd (LaunchAgent) — safe to call repeatedly.
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$BASE_DIR")"

export PYTHONPATH="$PARENT_DIR"

PYTHON="$PARENT_DIR/.venv/bin/python"
YT_UPLOADER="$PARENT_DIR/src/uploaders/yt_uploader.py"
IG_UPLOADER="$PARENT_DIR/src/uploaders/ig_uploader.py"
QUEUE="$PARENT_DIR/upload_queue"
UPLOADED="$PARENT_DIR/uploaded"
LOG="$PARENT_DIR/auto_last_upload.txt"

TODAY=$(date +%F)

echo "──────────────────────────────────────"
echo "  Auto-Uploader  [$TODAY]"
echo "──────────────────────────────────────"

# ── Sanity checks ──────────────────────────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo "❌ Python venv not found: $PYTHON"
    echo "   Run setup_all_venvs.sh first."
    exit 1
fi

# ── Check config ───────────────────────────────────────────────────────────
YT_ENABLED=$("$PYTHON" -c "
import sys
sys.path.insert(0, '$PARENT_DIR')
from src.upload_config import YOUTUBE_VIDEO
print('yes' if YOUTUBE_VIDEO and YOUTUBE_VIDEO not in ('none', '') else 'no')
" 2>/dev/null)

IG_ENABLED=$("$PYTHON" -c "
import sys
sys.path.insert(0, '$PARENT_DIR')
from src.upload_config import INSTAGRAM_VIDEO
print('yes' if INSTAGRAM_VIDEO and INSTAGRAM_VIDEO not in ('none', '') else 'no')
" 2>/dev/null)

echo "   YouTube:   ${YT_ENABLED}"
echo "   Instagram: ${IG_ENABLED}"
echo ""

if [ "$YT_ENABLED" != "yes" ] && [ "$IG_ENABLED" != "yes" ]; then
    echo "ℹ️  All uploads disabled in config."
    exit 0
fi

# ── Ensure folders exist ─────────────────────────────────────────────────────
mkdir -p "$QUEUE"
mkdir -p "$UPLOADED"

# ── Find video folder ───────────────────────────────────────────────────────
CHOSEN=""
FROM_QUEUE=false

# Check upload_queue first
for full in "$QUEUE"/*; do
    if [ ! -d "$full" ]; then continue; fi
    if [ -f "$full/final_video_mixed.mp4" ] || [ -f "$full/final_video_simple.mp4" ]; then
        if [ -f "$full/script.txt" ]; then
            CHOSEN="$full"
            FROM_QUEUE=true
            break
        fi
    fi
done

# Check uploaded/ for pending uploads
if [ -z "$CHOSEN" ]; then
    for full in "$UPLOADED"/*; do
        if [ ! -d "$full" ]; then continue; fi
        if [ -f "$full/final_video_mixed.mp4" ] || [ -f "$full/final_video_simple.mp4" ]; then
            if [ -f "$full/script.txt" ]; then
                # Check pending uploads based on config
                YT_PENDING=false
                IG_PENDING=false

                if [ "$YT_ENABLED" = "yes" ] && [ ! -f "$full/youtube_id.txt" ]; then
                    YT_PENDING=true
                fi
                if [ "$IG_ENABLED" = "yes" ] && [ ! -f "$full/ig_id.txt" ]; then
                    IG_PENDING=true
                fi

                if [ "$YT_PENDING" = true ] || [ "$IG_PENDING" = true ]; then
                    CHOSEN="$full"
                    break
                fi
            fi
        fi
    done
fi

if [ -z "$CHOSEN" ]; then
    echo "ℹ️  No videos waiting for upload."
    exit 0
fi

NAME=$(basename "$CHOSEN")
echo "📹 Found: $NAME"
echo ""

# ── Upload to YouTube ────────────────────────────────────────────────────────
if [ "$YT_ENABLED" = "yes" ]; then
    echo "🚀 YouTube upload..."
    "$PYTHON" "$YT_UPLOADER" "$CHOSEN"
    YT_EXIT=$?
    echo ""
else
    echo "⏭️  YouTube upload skipped (disabled)"
    YT_EXIT=0
fi

# ── Upload to Instagram ───────────────────────────────────────────────────────
if [ "$IG_ENABLED" = "yes" ]; then
    echo "🚀 Instagram upload..."
    "$PYTHON" "$IG_UPLOADER" "$CHOSEN"
    IG_EXIT=$?
    echo ""
else
    echo "⏭️  Instagram upload skipped (disabled)"
    IG_EXIT=0
fi

# ── Check completion ─────────────────────────────────────────────────────────
ALL_DONE=true
PENDING_LIST=""

if [ "$YT_ENABLED" = "yes" ] && [ ! -f "$CHOSEN/youtube_id.txt" ]; then
    ALL_DONE=false
    PENDING_LIST="$PENDING_LIST YouTube"
fi

if [ "$IG_ENABLED" = "yes" ] && [ ! -f "$CHOSEN/ig_id.txt" ]; then
    ALL_DONE=false
    PENDING_LIST="$PENDING_LIST Instagram"
fi

if [ "$ALL_DONE" = true ]; then
    echo "$TODAY" > "$LOG"
    if [ "$FROM_QUEUE" = true ]; then
        mv "$CHOSEN" "$UPLOADED/$NAME"
        echo "✅ All uploads complete! Moved → uploaded/$NAME"
    else
        echo "✅ All uploads complete for $NAME"
    fi
    echo "📅 Log updated → $TODAY"
    exit 0
else
    echo "ℹ️  Uploads pending:$PENDING_LIST - keeping in queue"
    if [ "$FROM_QUEUE" = false ]; then
        echo "   (in uploaded/ - will retry next run)"
    fi
    exit 0
fi
