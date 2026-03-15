#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# watch.sh - Run the watcher to auto-process new videos
# ─────────────────────────────────────────────────────────────────────────────

cd "$(dirname "$0")/.."

echo "----------------------------------------"
echo "🚀 STARTING YOUTUBE AUTOMATION WATCHER"
echo "----------------------------------------"
echo "Watching folder: yt_inbox/"
echo "Press Ctrl+C to stop..."

./.venv/bin/python src/watcher.py
