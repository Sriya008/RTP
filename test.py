# simple_test.py
try:
    import moviepy
    print("MoviePy version:", moviepy.__version__)
    from moviepy.editor import VideoFileClip
    print("VideoFileClip imported successfully")
except Exception as e:
    print(f"Error: {e}")