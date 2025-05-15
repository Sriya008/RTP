# pylint: disable=import-error
from moviepy.editor import VideoFileClip


def extract_audio(video_path, output_audio_path):
    """Extracts audio from a video file and saves it as a WAV file."""
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_audio_path)
        print(f"Audio extracted successfully: {output_audio_path}")
    except Exception as e:
        print(f"Error: {e}")

# Example Usage:
video_path = r"C:\Users\Sriya\RTP\vid.mp4"  # Change this to your video file path
output_audio_path = r"C:\Users\Sriya\RTP\audio.wav"  # Change this to your desired output path

extract_audio(video_path, output_audio_path)
