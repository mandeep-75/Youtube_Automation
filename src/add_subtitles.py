# add_subtitles.py
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip

def add_subtitles(video_path, script_path, output_path):
    # Load video
    video = VideoFileClip(video_path)
    
    # Read script
    with open(script_path, 'r') as f:
        script_text = f.read().strip()
    
    # Create a TextClip that lasts the whole video
    txt_clip = TextClip(script_text, fontsize=24, color='white', stroke_color='black', stroke_width=2)
    txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(video.duration)
    
    # Composite
    final = CompositeVideoClip([video, txt_clip])
    final.write_videofile(output_path, codec='libx264', audio_codec='aac')

if __name__ == "__main__":
    add_subtitles("outputs/video_without_subs.mp4", "outputs/script.txt", "outputs/final_video.mp4")