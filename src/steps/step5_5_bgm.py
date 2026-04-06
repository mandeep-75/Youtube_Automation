"""
Step 5.5: Generate Background Music via ComfyUI (ACE-Step 1.5)

Uses ComfyUI API to run the ACE-Step 1.5 workflow for music generation.
"""

import argparse
import os
import sys
import json
import time
import uuid
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src import config


class ComfyUIMusicGenerator:
    """Generate music using ComfyUI + ACE-Step 1.5."""

    def __init__(self, comfyui_url: str = None):
        self.comfyui_url = (comfyui_url or config.COMFYUI_URL).rstrip("/")
        self.api_url = f"{self.comfyui_url}/api"
        self.history_url = f"{self.comfyui_url}/history"

    def wait_for_queue(self, timeout: int = 300) -> str | None:
        """Wait for current queue to complete and return prompt ID."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.comfyui_url}/system_stats", timeout=5)
                if resp.status_code == 200:
                    stats = resp.json()
                    # Check if anything is running
                    if stats.get("memory", {}).get("vram_used", 0) > 0:
                        time.sleep(2)
                        continue
                return None
            except Exception:
                pass
            time.sleep(1)
        return None

    def generate_music(
        self,
        duration: float,
        tags: str = "epic cinematic ambient background music",
        lyrics: str = None,
        bpm: int = 120,
        keyscale: str = "C minor",
        seed: int = None,
    ) -> str:
        """
        Generate music via ComfyUI workflow.

        Args:
            duration: Duration in seconds
            tags: Music style/tags description
            lyrics: Optional lyrics
            bpm: Beats per minute
            keyscale: Musical key
            seed: Random seed

        Returns:
            Path to generated audio file
        """
        if seed is None:
            seed = int(time.time()) % 2147483647

        print(f"[ace-step] Connecting to ComfyUI at {self.comfyui_url}...")

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

        print(f"[ace-step] Generating {duration}s music...")
        print(f"[ace-step] Style: {tags}")

        # Build workflow with dynamic inputs
        workflow = self._build_workflow(
            duration=duration,
            tags=tags,
            lyrics=lyrics,
            bpm=bpm,
            keyscale=keyscale,
            seed=seed,
        )

        # Submit workflow
        prompt_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "prompt_id": prompt_id}

        print(f"[ace-step] Submitting job...")
        resp = requests.post(self.api_url + "/prompt", json=payload, timeout=30)

        if resp.status_code != 200:
            raise Exception(
                f"Failed to submit workflow: {resp.status_code} - {resp.text}"
            )

        result = resp.json()
        if result.get("error"):
            raise Exception(f"Workflow error: {result['error']}")

        # Wait for completion
        print(f"[ace-step] Waiting for generation...")
        output_path = self._wait_for_completion(
            prompt_id, timeout=int(duration * 10 + 120)
        )

        return output_path

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
        # Load base workflow
        workflow_path = config.COMFYUI_WORKFLOW_PATH
        with open(workflow_path, "r") as f:
            workflow = json.load(f)

        # Update TextEncodeAceStepAudio1.5 node (94)
        if "94" in workflow:
            workflow["94"]["inputs"]["tags"] = tags
            workflow["94"]["inputs"]["duration"] = int(duration)
            workflow["94"]["inputs"]["seed"] = seed
            workflow["94"]["inputs"]["bpm"] = bpm
            workflow["94"]["inputs"]["keyscale"] = keyscale
            if lyrics:
                workflow["94"]["inputs"]["lyrics"] = lyrics
            else:
                # Remove lyrics for instrumental
                workflow["94"]["inputs"]["lyrics"] = ""

        # Update EmptyAceStep1.5LatentAudio node (98)
        if "98" in workflow:
            workflow["98"]["inputs"]["seconds"] = int(duration)

        # Update KSampler node (3) with new seed
        if "3" in workflow:
            workflow["3"]["inputs"]["seed"] = seed

        return workflow

    def _wait_for_completion(self, prompt_id: str, timeout: int = 300) -> str:
        """Wait for workflow to complete and return output path."""
        start_time = time.time()
        last_check = 0

        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.history_url}/{prompt_id}", timeout=10)
                if resp.status_code == 200:
                    history = resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})

                        # Find the SaveAudioMP3 node (107) output
                        for node_id, node_output in outputs.items():
                            if node_output.get("class_type") == "SaveAudioMP3":
                                if "audio_path" in node_output:
                                    audio_path = node_output["audio_path"]
                                    print(f"[ace-step] ✅ Generated: {audio_path}")
                                    return audio_path
                                elif "ui" in node_output:
                                    # ComfyUI UI format
                                    ui_data = node_output["ui"]
                                    if "audio" in ui_data:
                                        filename = ui_data["audio"][0]["name"]
                                        # Construct full path
                                        output_dir = os.path.join(
                                            config.PROJECT_ROOT,
                                            "..",
                                            "Downloads",
                                            "comfy",
                                            "output",
                                        )
                                        audio_path = os.path.join(output_dir, filename)
                                        print(f"[ace-step] ✅ Generated: {audio_path}")
                                        return audio_path

                        # Check for any audio output
                        for node_id, node_output in outputs.items():
                            if "audio" in node_output or "ui" in node_output:
                                ui = node_output.get("ui", {})
                                if "audio" in ui:
                                    filename = ui["audio"][0]["name"]
                                    output_dir = os.path.join(
                                        config.PROJECT_ROOT,
                                        "..",
                                        "Downloads",
                                        "comfy",
                                        "output",
                                    )
                                    return os.path.join(output_dir, filename)

                        # Workflow completed but no audio found
                        print(
                            f"[ace-step] ⚠️ Workflow completed but audio not found in outputs"
                        )
                        return None

                # Check every 3 seconds
                if time.time() - last_check > 3:
                    elapsed = int(time.time() - start_time)
                    print(f"[ace-step] Still generating... ({elapsed}s)")
                    last_check = time.time()

            except Exception as e:
                print(f"[ace-step] Error checking status: {e}")

            time.sleep(1)

        raise TimeoutError(f"Music generation timed out after {timeout}s")


def infer_music_style(script_text: str) -> str:
    """Use Ollama to infer music style from script."""
    try:
        import ollama

        prompt = f"""Based on this narration script, suggest music tags for background music.
        Return ONLY the tags/description (e.g., "epic cinematic", "chill lofi", "intense action").
        Focus on mood, energy, and instrumentation.
        
        Script: {script_text[:800]}...
        
        Music tags:"""

        response = ollama.generate(
            model="qwen3.5:0.8b",
            prompt=prompt,
            options={"num_predict": 100},
        )

        style = response["response"].strip()
        print(f"[ace-step] Inferred style: {style}")
        return style if style else "epic cinematic ambient"

    except Exception as e:
        print(f"[ace-step] Could not infer style: {e}")
        return "epic cinematic ambient"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate background music via ComfyUI + ACE-Step 1.5"
    )
    parser.add_argument(
        "--script", help="Path to narration script (for style inference)"
    )
    parser.add_argument(
        "--duration", type=float, required=True, help="Duration in seconds"
    )
    parser.add_argument(
        "--output", default="outputs/bgm.wav", help="Output music file path"
    )
    parser.add_argument(
        "--tags",
        default="epic cinematic ambient background music",
        help="Music style tags",
    )
    parser.add_argument("--lyrics", default=None, help="Optional lyrics")
    parser.add_argument("--bpm", type=int, default=120, help="Beats per minute")
    parser.add_argument("--keyscale", default="C minor", help="Musical key")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--infer-style", action="store_true", help="Infer style from script"
    )
    parser.add_argument("--comfyui-url", default=None, help="ComfyUI URL")
    args = parser.parse_args()

    # Read script for style inference
    script_text = ""
    if args.script and os.path.isfile(args.script):
        with open(args.script, "r", encoding="utf-8") as f:
            script_text = f.read().strip()

    # Infer style if requested
    tags = args.tags
    if args.infer_style and script_text:
        tags = infer_music_style(script_text)

    # Generate music
    generator = ComfyUIMusicGenerator(comfyui_url=args.comfyui_url)

    try:
        audio_path = generator.generate_music(
            duration=args.duration,
            tags=tags,
            lyrics=args.lyrics,
            bpm=args.bpm,
            keyscale=args.keyscale,
            seed=args.seed,
        )

        if audio_path and os.path.exists(audio_path):
            # Copy to desired output location
            import shutil

            output_dir = os.path.dirname(args.output) or "outputs"
            os.makedirs(output_dir, exist_ok=True)

            dest_path = args.output
            if dest_path.endswith(".mp3"):
                dest_path = dest_path.replace(".mp3", ".wav")

            shutil.copy(audio_path, dest_path)
            print(f"[ace-step] ✅ Music copied to: {dest_path}")
        else:
            print(f"[ace-step] ⚠️ Generated audio not found at expected path")
            if audio_path:
                print(f"[ace-step]   Found at: {audio_path}")

    except Exception as e:
        print(f"[ace-step] ❌ Error: {e}")
        sys.exit(1)
