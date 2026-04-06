"""
Step 5.6: Mix Audio Tracks

Mixes TTS narration with background music into a final audio track.
Supports multiple mixing modes and volume control.
"""

import argparse
import os
import sys

import numpy as np
import soundfile as sf


def get_audio_duration(filepath: str) -> float:
    """Get audio file duration in seconds."""
    info = sf.info(filepath)
    return info.frames / info.samplerate


def mix_audio(
    narration_path: str,
    music_path: str,
    output_path: str,
    narration_volume: float = 1.0,
    music_volume: float = 0.25,
    fade_in: float = 0.5,
    fade_out: float = 1.0,
    crossfade: float = 0.5,
) -> str:
    """
    Mix narration with background music.

    Args:
        narration_path: Path to TTS narration audio
        music_path: Path to background music
        output_path: Output path for mixed audio
        narration_volume: Volume multiplier for narration (0.0-1.0)
        music_volume: Volume multiplier for music (0.0-1.0)
        fade_in: Music fade-in duration in seconds
        fade_out: Music fade-out duration in seconds
        crossfade: Crossfade duration at the end

    Returns:
        Path to mixed audio file
    """
    print(f"[mixer] Loading audio files...")

    # Load narration
    narration, sr_nar = sf.read(narration_path)
    if len(narration.shape) > 1:
        narration = narration.mean(axis=1)  # Convert to mono

    # Load music
    music, sr_mus = sf.read(music_path)
    if len(music.shape) > 1:
        music = music.mean(axis=1)  # Convert to mono

    # Use narration sample rate
    sample_rate = sr_nar

    # Calculate target length (match narration length)
    target_length = len(narration)
    music_length = len(music)

    print(f"[mixer] Narration: {len(narration) / sample_rate:.1f}s")
    print(f"[mixer] Music: {len(music) / sample_rate:.1f}s")

    # Extend music to match narration (loop if needed)
    if music_length < target_length:
        # Calculate how many times we need to loop
        repeats = (target_length // music_length) + 2
        music = np.tile(music, repeats)
        print(f"[mixer] Looped music {repeats} times")

    # Trim to narration length
    music = music[:target_length]

    # Apply fades to music
    fade_in_samples = int(fade_in * sample_rate)
    fade_out_samples = int(fade_out * sample_rate)

    # Fade in
    if fade_in_samples > 0:
        fade_in_curve = np.linspace(0, 1, min(fade_in_samples, len(music)))
        music[: len(fade_in_curve)] *= fade_in_curve

    # Fade out
    if fade_out_samples > 0:
        fade_out_curve = np.linspace(1, 0, min(fade_out_samples, len(music)))
        music[-len(fade_out_curve) :] *= fade_out_curve

    # Apply volumes
    narration = narration * narration_volume
    music = music * music_volume

    # Mix
    mixed = narration + music

    # Normalize to prevent clipping
    max_val = np.abs(mixed).max()
    if max_val > 1.0:
        mixed = mixed / max_val * 0.95
        print(f"[mixer] Normalized to prevent clipping")

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, mixed, sample_rate)

    print(f"[mixer] ✅ Mixed audio saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mix narration with background music")
    parser.add_argument(
        "--narration", required=True, help="Path to TTS narration audio"
    )
    parser.add_argument("--music", required=True, help="Path to background music")
    parser.add_argument("--output", required=True, help="Output mixed audio path")
    parser.add_argument(
        "--narration-volume", type=float, default=1.0, help="Narration volume (0.0-1.0)"
    )
    parser.add_argument(
        "--music-volume", type=float, default=0.25, help="Music volume (0.0-1.0)"
    )
    parser.add_argument(
        "--fade-in", type=float, default=0.5, help="Music fade-in duration (seconds)"
    )
    parser.add_argument(
        "--fade-out", type=float, default=1.0, help="Music fade-out duration (seconds)"
    )
    args = parser.parse_args()

    mix_audio(
        narration_path=args.narration,
        music_path=args.music,
        output_path=args.output,
        narration_volume=args.narration_volume,
        music_volume=args.music_volume,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
    )
