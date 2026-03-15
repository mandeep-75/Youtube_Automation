#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Instagram Uploader (Graph API - Official)
# Uses Meta's official Instagram Graph API for Reels
#
# SETUP:
# 1. Access token and User ID already configured in .env
# 2. Run: bash scripts/ig_service.sh
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$BASE_DIR")"

PYTHON="$PARENT_DIR/.venv/bin/python"
UPLOADER="$PARENT_DIR/src/uploaders/ig_worker.py"
QUEUE="$PARENT_DIR/upload_queue"
UPLOADED="$PARENT_DIR/uploaded"
LOG="$PARENT_DIR/ig_last_upload.txt"

TODAY=$(date +%F)

echo "──────────────────────────────────────"
echo "  Instagram Graph API Uploader  [$TODAY]"
echo "──────────────────────────────────────"

# Sanity checks
if [ ! -f "$PYTHON" ]; then
    echo "❌ Uploader venv not found: $PYTHON"
    exit 1
fi

if [ ! -f "$UPLOADER" ]; then
    echo "❌ Uploader script not found: $UPLOADER"
    exit 1
fi

# Check env vars
if [ -z "$IG_GRAPH_ACCESS_TOKEN" ]; then
    source "$PARENT_DIR/.env" 2>/dev/null || true
fi

if [ -z "$IG_GRAPH_ACCESS_TOKEN" ]; then
    echo "❌ IG_GRAPH_ACCESS_TOKEN not set"
    echo "   Add to .env: IG_GRAPH_ACCESS_TOKEN=your_access_token"
    exit 1
fi

if [ -z "$IG_GRAPH_USER_ID" ]; then
    echo "❌ IG_GRAPH_USER_ID not set"
    echo "   Add to .env: IG_GRAPH_USER_ID=your_instagram_id"
    exit 1
fi

# Ensure folders exist
mkdir -p "$QUEUE"
mkdir -p "$UPLOADED"

# Find video to upload
CHOSEN=""

for full in "$QUEUE"/*; do
    if [ ! -d "$full" ]; then continue; fi
    if [ -f "$full/final_video.mp4" ] && [ -f "$full/script.txt" ] && [ ! -f "$full/ig_id.txt" ]; then
        CHOSEN="$full"
        break
    fi
done

if [ -z "$CHOSEN" ]; then
    echo "ℹ️  No videos waiting for Instagram upload."
    exit 0
fi

echo "📹 Found: $(basename "$CHOSEN")"
echo "🚀 Uploading to Instagram (Graph API)..."

"$PYTHON" "$UPLOADER" "$CHOSEN"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$TODAY" > "$LOG"
    echo "✅ Done!"
else
    echo "❌ Upload failed (exit $EXIT_CODE)."
    exit $EXIT_CODE
fi