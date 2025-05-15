import srt
from datetime import timedelta

def generate_srt(transcript, output_srt_path):
    """Generates SRT subtitle file from text."""
    subtitles = []
    words = transcript.split()
    start_time = timedelta(seconds=0)

    for i, word in enumerate(words):
        end_time = start_time + timedelta(seconds=1)
        subtitles.append(srt.Subtitle(index=i+1, start=start_time, end=end_time, content=word))
        start_time = end_time

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))

# Example usage
# generate_srt("भारत एक महान देश है।", "output.srt")
