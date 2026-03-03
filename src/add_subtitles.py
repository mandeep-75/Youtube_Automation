# add_subtitles.py
import random
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

def random_color():
    """Generate a random color in hex or name."""
    colors = ['white', 'yellow', 'cyan', 'magenta', 'orange', 'lime', 'pink']
    return random.choice(colors)

def add_subtitles(video_path, script_path, output_path):
    # Load video
    video = VideoFileClip(video_path)
    
    # Read script
    with open(script_path, 'r') as f:
        script_text = f.read().strip()
    
    # Split text into words
    words = script_text.split()
    
    # Duration per word (evenly spread over video)
    duration_per_word = video.duration / max(len(words), 1)
    
    # Create TextClips for each word with random color
    clips = []
    for i, word in enumerate(words):
        color = random_color()
        txt_clip = (TextClip(word, fontsize=24, color=color, stroke_color='black', stroke_width=2)
                    .set_position(('center', 'bottom'))
                    .set_start(i * duration_per_word)
                    .set_duration(duration_per_word))
        clips.append(txt_clip)
    
    # Composite video
    final = CompositeVideoClip([video, *clips])
    final.write_videofile(output_path, codec='libx264', audio_codec='aac')

if __name__ == "__main__":
    add_subtitles("outputs/video_without_subs.mp4", "outputs/script.txt", "outputs/final_video.mp4")