#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# auto_service.sh
# Unified auto-uploader that routes video versions to appropriate platforms
# based on config settings.
#
# HOW TO USE:
#   1. Drop a folder into upload_queue/ (must have final_video_mixed.mp4,
#      final_video_simple.mp4, and script.txt)
#   2. This script runs automatically on boot and every 24 hours.
#   3. After both uploads complete, folder is moved to uploaded/
#
# Called by launchd (LaunchAgent) — safe to call repeatedly.
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$BASE_DIR")"

# Add project root to Python path
export PYTHONPATH="$PARENT_DIR"

PYTHON="$PARENT_DIR/.venv/bin/python"
UPLOADER="$PARENT_DIR/src/uploaders/auto_uploader.py"
QUEUE="$PARENT_DIR/upload_queue"
UPLOADED="$PARENT_DIR/uploaded"
LOG="$PARENT_DIR/auto_last_upload.txt"

TODAY=$(date +%F)

echo "──────────────────────────────────────"
echo "  Auto-Uploader  [$TODAY]"
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

# ── Ensure folders exist ─────────────────────────────────────────────────────
mkdir -p "$QUEUE"
mkdir -p "$UPLOADED"

# ── Find video folder ───────────────────────────────────────────────────────
CHOSEN=""

for full in "$QUEUE"/*; do
    if [ ! -d "$full" ]; then continue; fi
    
    # Need both video versions and script
    if [ -f "$full/final_video_mixed.mp4" ] || [ -f "$full/final_video_simple.mp4" ]; then
        if [ -f "$full/script.txt" ]; then
            CHOSEN="$full"
            break
        fi
    fi
done

# If nothing in queue, check uploaded/ for pending uploads
if [ -z "$CHOSEN" ]; then
    for full in "$UPLOADED"/*; do
        if [ ! -d "$full" ]; then continue; fi
        if [ -f "$full/final_video_mixed.mp4" ] || [ -f "$full/final_video_simple.mp4" ]; then
            if [ -f "$full/script.txt" ]; then
                # Check if uploads are pending (id files missing)
                if [ ! -f "$full/youtube_id.txt" ] || [ ! -f "$full/ig_id.txt" ]; then
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

# ── Run auto-uploader ───────────────────────────────────────────────────────
"$PYTHON" "$UPLOADER" "$CHOSEN"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$TODAY" > "$LOG"
    
    # Check if both uploads are done
    YT_DONE=false
    IG_DONE=false
    
    # Check YouTube (if enabled)
    if [ -f "$CHOSEN/youtube_id.txt" ]; then
        YT_DONE=true
    fi
    
    # Check Instagram (if enabled)
    if [ -f "$CHOSEN/ig_id.txt" ]; then
        IG_DONE=true
    fi
    
    # Move to uploaded/ if both platforms done
    if [ "$YT_DONE" = true ] && [ "$IG_DONE" = true ]; then
        if [[ "$CHOSEN" == "$QUEUE"* ]]; then
            mv "$CHOSEN" "$UPLOADED/$NAME"
            echo "✅ Done! Moved → uploaded/$NAME"
        else
            echo "✅ All uploads complete for $NAME"
        fi
    else
        echo "ℹ️  Uploads pending - keeping in queue"
        [ "$YT_DONE" = true ] && echo "   ✓ YouTube done"
        [ "$IG_DONE" = true ] && echo "   ✓ Instagram done"
    fi
    
    echo "📅 Log updated → $TODAY"
else
    echo "❌ Upload failed (exit $EXIT_CODE)."
    exit $EXIT_CODE
fi
