#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_all_venvs.sh
# Builds ALL project venvs in one shot.
# Run from the project root:  bash setup_all_venvs.sh
# ---------------------------------------------------------------------------
set -euo pipefail

echo "════════════════════════════════════════════"
echo "  Setting up faster_whisper venv"
echo "════════════════════════════════════════════"
bash venvs/faster_whisper/setup.sh

echo ""
echo "════════════════════════════════════════════"
echo "  Setting up chatterbox venv"
echo "════════════════════════════════════════════"
bash venvs/chatterbox/setup.sh

echo ""
echo "✅  All venvs are ready!"
echo ""
echo "  faster_whisper : venvs/faster_whisper/bin/python"
echo "  chatterbox     : venvs/chatterbox/bin/python"
echo ""
echo "  Run the pipeline:"
echo "    python pipeline.py <your_video.mp4>"
