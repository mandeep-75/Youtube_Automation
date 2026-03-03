#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_all_venvs.sh
# Builds ALL project venvs in one shot.
# Run from the project root:  bash setup_all_venvs.sh
# ---------------------------------------------------------------------------
set -euo pipefail

# resolve project root (directory containing this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# start with a clean slate by removing any previously-built venvs
if [ -d "$PROJECT_ROOT/venvs" ]; then
    echo "🧹 Removing existing virtual environments under $PROJECT_ROOT/venvs"
    rm -rf "$PROJECT_ROOT/venvs"
fi
# ensure venvs directory exists even before any environment is created
mkdir -p "$PROJECT_ROOT/venvs"

# We used to have separate helpers under venvs/*/setup.sh but they
# were never committed; instead recreate the venvs directly here so the
# bootstrap works out of the box and can also clean existing environments.

# ---------------------- Python version detection -------------------------
# chatterbox-tts currently requires Python 3.11.  Look for an interpreter
# that provides that version and fail early if it's missing.
find_python311() {
    for cmd in python3.11 python3 python; do
        if command -v "$cmd" >/dev/null; then
            ver=$($cmd -c 'import sys; print("{}.{}".format(*sys.version_info[:2]))')
            if [[ "$ver" == "3.11"* ]]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD=$(find_python311) || {
    echo "ERROR: no Python 3.11 interpreter found."
    echo "Install Python 3.11 (e.g. 'brew install python@3.11' on macOS)"
    exit 1
}

echo "Using interpreter: $PYTHON_CMD"

# helper to create an isolated venv from a requirements file
create_venv() {
    local name="$1" reqfile="$2"
    echo "════════════════════════════════════════════"
    echo "  Creating venv '$name'"
    echo "════════════════════════════════════════════"
    rm -rf "$PROJECT_ROOT/venvs/$name"
    "$PYTHON_CMD" -m venv "$PROJECT_ROOT/venvs/$name"
    "$PROJECT_ROOT/venvs/$name/bin/python" -m pip install --upgrade pip setuptools wheel
    "$PROJECT_ROOT/venvs/$name/bin/python" -m pip install -r "$reqfile"
}

# build the two project venvs
create_venv chatterbox "$PROJECT_ROOT/requirements_chatterbox.txt"
create_venv faster_whisper "$PROJECT_ROOT/requirements_whisper.txt"

echo ""
echo "════════════════════════════════════════════"
echo "  Setting up fastvlm conda env"
echo "════════════════════════════════════════════"

if command -v conda >/dev/null; then
    if conda env list | grep -q '^fastvlm'; then
        echo "Removing existing conda environment 'fastvlm'"
        conda env remove -n fastvlm -y
    fi
    echo "Creating conda env 'fastvlm' (python 3.10)"
    conda create -n fastvlm python=3.10 -y

    # install the main project into the conda env so fastvlm_describe.py works
    # the project is defined by pyproject.toml at the repository root
    echo "Installing project dependencies into fastvlm env (using pyproject.toml)"
    conda run -n fastvlm pip install -e "$PROJECT_ROOT"
else
    echo "⚠️  conda not found; skipping fastvlm environment setup"
    echo "    (install Miniforge/Anaconda if you want the LLaVA/fastvlm step)"
fi


echo "✅  All environments are ready!"
echo "Note: the venv directories under 'venvs/' are purposely gitignored."
echo "      You can re-run this script on any fresh clone without errors."
echo ""
echo "Available interpreters:"
echo "  faster_whisper : venvs/faster_whisper/bin/python"
echo "  chatterbox     : venvs/chatterbox/bin/python"
echo "  fastvlm        : activate with 'conda activate fastvlm'"
echo ""
echo "Run the pipeline:"
echo "    python pipeline.py <your_video.mp4>"
