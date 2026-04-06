"""
Step 5: Generate Narration with Background Music via ACE-Step 1.5

Replaces TTS (Chatterbox) with ACE-Step 1.5.
The script becomes the lyrics, and ACE-Step generates vocals + background music.
"""

import argparse
import os
import re
import sys
import json
import time
import uuid
from typing import Optional
import requests
import shutil

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


class ComfyUITTS:
    """Generate narration + music using ComfyUI + ACE-Step 1.5."""

    def __init__(self, comfyui_url: Optional[str] = None):
        self.comfyui_url = (comfyui_url or config.COMFYUI_URL).rstrip("/")
        self.api_url = f"{self.comfyui_url}/api"
        self.history_url = f"{self.comfyui_url}/history"

    def generate(
        self,
        script_text: str,
        duration: float,
        output_path: str,
        style: str = "epic cinematic ambient pop",
        bpm: int = 120,
        keyscale: str = "C minor",
        seed: Optional[int] = None,
    ) -> str:
        """
        Generate audio via ACE-Step 1.5.
        The script becomes lyrics, and ACE-Step generates vocals + music.

        Args:
            script_text: The narration script (will become lyrics)
            duration: Target duration in seconds
            output_path: Where to save the audio
            style: Music style description
            bpm: Beats per minute
            keyscale: Musical key
            seed: Random seed

        Returns:
            Path to generated audio file
        """
        if seed is None:
            seed = int(time.time()) % 2147483647

        print(f"[ace-tts] Connecting to ComfyUI at {self.comfyui_url}...")

        # Check ComfyUI is running
        try:
            resp = requests.get(f"{self.comfyui_url}/system_stats", timeout=5)
            if resp.status_code != 200:
                raise Exception(f"ComfyUI returned status {resp.status_code}")
        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Cannot connect to ComfyUI at {self.comfyui_url}. "
                "Please ensure ComfyUI is running."
            )

        # Format script as lyrics
        lyrics = self._format_script_as_lyrics(script_text, duration)

        print(f"[ace-tts] Generating {duration}s audio...")
        print(f"[ace-tts] Style: {style}")
        print(f"[ace-tts] Lyrics length: {len(lyrics)} chars")

        # Build workflow with dynamic inputs
        workflow = self._build_workflow(
            duration=duration,
            tags=style,
            lyrics=lyrics,
            bpm=bpm,
            keyscale=keyscale,
            seed=seed,
        )

        # Submit workflow
        prompt_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "prompt_id": prompt_id}

        print("[ace-tts] Submitting job...")
        resp = requests.post(self.api_url + "/prompt", json=payload, timeout=30)

        if resp.status_code != 200:
            raise Exception(
                f"Failed to submit workflow: {resp.status_code} - {resp.text}"
            )

        result = resp.json()
        if result.get("error") is not None:
            raise Exception(f"Workflow error: {result['error']}")

        # Wait for completion
        print("[ace-tts] Generating audio (this may take a while)...")
        audio_path = self._wait_for_completion(
            prompt_id, timeout=int(duration * 15 + 180)
        )

        if audio_path and os.path.exists(audio_path):
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            shutil.copy(audio_path, output_path)
            print(f"[ace-tts] ✅ Audio saved to: {output_path}")
            return output_path
        else:
            raise Exception("Audio generation completed but file not found")

    def _format_script_as_lyrics(self, script: str, duration: float) -> str:
        """
        Convert script text into lyrics format for ACE-Step.
        ACE-Step expects lyrics with verse/chorus markers and timing.
        """
        script = script.strip()

        if not script:
            raise ValueError("Script text cannot be empty")

        # Check for existing markers - if found, return as-is
        if re.search(r"\[(Verse|Chorus|Bridge|Pre-Chorus)\]", script, re.IGNORECASE):
            return script

        # Fall back to auto-formatting for non-structured scripts
        return self._auto_format_lyrics(script)

    def _auto_format_lyrics(self, script: str) -> str:
        """Auto-format plain text script into lyrics with markers."""
        words = script.split()
        lines: list[str] = []
        current_line: list[str] = []
        words_per_line = 10

        for word in words:
            current_line.append(word)
            if len(current_line) >= words_per_line:
                lines.append(" ".join(current_line))
                current_line = []

        if current_line:
            lines.append(" ".join(current_line))

        verses: list[str] = []
        verse_size = 4
        for i in range(0, len(lines), verse_size):
            verse_chunk: list[str] = lines[i : i + verse_size]
            if verse_chunk:
                verses.append("\n".join(verse_chunk))

        lyrics_parts: list[str] = []
        verse_markers: list[str] = ["[Verse]", "[Pre-Chorus]", "[Chorus]", "[Bridge]"]

        for i, verse in enumerate(verses):
            marker_idx = min(i, len(verse_markers) - 1)
            marker: str = verse_markers[marker_idx]
            lyrics_parts.append(f"{marker}\n{verse}")

        return "\n\n".join(lyrics_parts)

    def _build_workflow(
        self,
        duration: float,
        tags: str,
        lyrics: str,
        bpm: int,
        keyscale: str,
        seed: int,
    ) -> dict:
        """Build the workflow with dynamic parameters."""
        workflow_path = config.COMFYUI_WORKFLOW_PATH

        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"ComfyUI workflow not found: {workflow_path}")

        with open(workflow_path, "r") as f:
            workflow = json.load(f)

        # Validate required nodes exist
        required_nodes = ["94", "98", "3"]
        missing_nodes = [n for n in required_nodes if n not in workflow]
        if missing_nodes:
            raise Exception(f"Workflow missing required nodes: {missing_nodes}")

        # Update TextEncodeAceStepAudio1.5 node (94)
        workflow["94"]["inputs"]["tags"] = tags
        workflow["94"]["inputs"]["duration"] = int(duration)
        workflow["94"]["inputs"]["seed"] = seed
        workflow["94"]["inputs"]["bpm"] = bpm
        workflow["94"]["inputs"]["keyscale"] = keyscale
        workflow["94"]["inputs"]["lyrics"] = lyrics
        workflow["94"]["inputs"]["generate_audio_codes"] = True

        # Update EmptyAceStep1.5LatentAudio node (98)
        workflow["98"]["inputs"]["seconds"] = int(duration)

        # Update KSampler node (3) with new seed
        workflow["3"]["inputs"]["seed"] = seed

        return workflow

    def _wait_for_completion(self, prompt_id: str, timeout: int = 600) -> Optional[str]:
        """Wait for workflow to complete and return output path."""
        start_time = time.time()
        last_check: float = 0

        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.history_url}/{prompt_id}", timeout=10)
                if resp.status_code == 200:
                    history = resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})

                        if not outputs:
                            pass  # Still generating

                        # Find audio output
                        audio_path = self._extract_audio_path(outputs)
                        if audio_path:
                            return audio_path

                        return None

                # Check every 5 seconds
                if time.time() - last_check > 5:
                    elapsed = int(time.time() - start_time)
                    print(f"[ace-tts] Still generating... ({elapsed}s)")
                    last_check = time.time()

            except Exception as e:
                print(f"[ace-tts] Error checking status: {e}")

            time.sleep(1)

        # Fallback: search ComfyUI output directory for most recent mp3
        return self._find_latest_audio()

    def _extract_audio_path(self, outputs: dict) -> Optional[str]:
        """Extract audio path from workflow outputs."""
        for node_id, node_output in outputs.items():
            # Structure 1: {"audio": [{"filename": "...", ...}]}
            if "audio" in node_output:
                audio_data = node_output["audio"]
                if isinstance(audio_data, list) and audio_data:
                    audio_item = audio_data[0]
                    # Handle both string and dict formats
                    if isinstance(audio_item, str):
                        filename = audio_item
                    elif isinstance(audio_item, dict):
                        filename = audio_item.get("filename") or audio_item.get(
                            "name", ""
                        )
                    else:
                        filename = ""
                    if filename:
                        return os.path.join(config.COMFYUI_OUTPUT_DIR, filename)
            # Structure 2: {"ui": {"audio": [...]}}
            elif "ui" in node_output:
                ui_data = node_output["ui"]
                if "audio" in ui_data:
                    audio_list = ui_data["audio"]
                    if isinstance(audio_list, list) and audio_list:
                        audio_item = audio_list[0]
                        filename = (
                            audio_item.get("filename", "")
                            if isinstance(audio_item, dict)
                            else str(audio_item)
                        )
                        if filename:
                            return os.path.join(config.COMFYUI_OUTPUT_DIR, filename)
            # Structure 3: {"audio_path": "/path/to/file"}
            elif "audio_path" in node_output:
                return node_output["audio_path"]
        return None

    def _find_latest_audio(self) -> Optional[str]:
        """Fallback: find most recent audio file in ComfyUI output directory."""
        output_dir = config.COMFYUI_OUTPUT_DIR
        if not os.path.exists(output_dir):
            print(f"[ace-tts] Fallback: Output directory not found: {output_dir}")
            return None

        # Find most recent mp3 file
        mp3_files = [
            os.path.join(output_dir, f)
            for f in os.listdir(output_dir)
            if f.endswith(".mp3")
        ]

        if not mp3_files:
            print(f"[ace-tts] Fallback: No mp3 files found in {output_dir}")
            return None

        # Return most recently modified
        latest = max(mp3_files, key=os.path.getmtime)
        print(f"[ace-tts] Fallback: Using latest audio: {latest}")
        return latest


def infer_music_style(script_text: str) -> str:
    """Use Ollama to infer music style from script content."""
    try:
        import ollama

        prompt = f"""Based on this narration script for a YouTube short, suggest music tags.
        Return ONLY the music style description (e.g., "epic cinematic", "chill lofi", "upbeat pop").
        Focus on mood, energy, and instrumentation that matches the narration tone.
        
        Script: {script_text[:600]}...
        
        Music style tags:"""

        response = ollama.generate(
            model=config.LLM_MODEL,
            prompt=prompt,
            options={"num_predict": 80},
            stream=False,
        )

        style = response["response"].strip()
        print(f"[ace-tts] Inferred style: {style}")
        return style if style else config.MUSIC_STYLE

    except Exception as e:
        print(f"[ace-tts] Could not infer style: {e}")
        return config.MUSIC_STYLE


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate narration with music via ACE-Step 1.5 (replaces TTS)"
    )
    parser.add_argument("--script", required=True, help="Path to narration script")
    parser.add_argument(
        "--duration", type=float, required=True, help="Duration in seconds"
    )
    parser.add_argument(
        "--output", default="outputs/voice.mp3", help="Output audio file"
    )
    parser.add_argument("--style", default=config.MUSIC_STYLE, help="Music style")
    parser.add_argument(
        "--bpm", type=int, default=config.MUSIC_BPM, help="Beats per minute"
    )
    parser.add_argument("--keyscale", default=config.MUSIC_KEYSCALE, help="Musical key")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--infer-style", action="store_true", help="Infer style from script"
    )
    parser.add_argument("--comfyui-url", default=None, help="ComfyUI URL")
    args = parser.parse_args()

    # Read script
    with open(args.script, "r", encoding="utf-8") as f:
        script_text = f.read().strip()

    # Infer style if requested
    style = args.style
    if args.infer_style:
        style = infer_music_style(script_text)

    # Generate audio
    generator = ComfyUITTS(comfyui_url=args.comfyui_url)

    try:
        generator.generate(
            script_text=script_text,
            duration=args.duration,
            output_path=args.output,
            style=style,
            bpm=args.bpm,
            keyscale=args.keyscale,
            seed=args.seed,
        )
    except Exception as e:
        print(f"[ace-tts] ❌ Error: {e}")
        sys.exit(1)
