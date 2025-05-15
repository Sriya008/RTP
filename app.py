from flask import Flask, request, jsonify, send_file, render_template
import os
import wave
import json
import srt
from datetime import timedelta
from moviepy.editor import VideoFileClip
from vosk import Model, KaldiRecognizer
from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator
from aksharamukha import transliterate

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
SUBTITLE_FOLDER = "subtitles"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUBTITLE_FOLDER, exist_ok=True)

# Use absolute path to Vosk model
VOSK_MODEL_PATH = r"C:\Users\Sriya\RTP\vosk-model-en-us-0.22"

# Extract audio from video and convert to WAV
def extract_audio(video_path, output_audio_path):
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            print(f"❌ No audio track found in video: {video_path}")
            raise ValueError("No audio track in video file")
            
        # Force proper format for Vosk (16kHz mono)
        audio = video.audio
        audio.write_audiofile(
            output_audio_path,
            fps=16000,
            nbytes=2,  # 16-bit audio
            codec='pcm_s16le',
            ffmpeg_params=["-ac", "1"]  # Force mono channel
        )
        print(f"✅ Audio extracted: {output_audio_path}")
        return True
    except Exception as e:
        print(f"❌ Audio extraction error: {e}")
        return False

# Verify audio is in correct format for Vosk
def verify_audio_format(audio_path):
    try:
        with wave.open(audio_path, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                print(f"❌ Audio format incorrect: channels={wf.getnchannels()}, rate={wf.getframerate()}")
                return False
        return True
    except Exception as e:
        print(f"❌ Error verifying audio format: {e}")
        return False

# Transcribe audio using Vosk
def transcribe_audio(audio_path, model_path):
    print("🔍 Loading Vosk model from:", model_path)
    
    # Use the provided model path parameter
    model = Model(model_path)

    wf = wave.open(audio_path, "rb")
    if wf.getnchannels() != 1 or wf.getframerate() != 16000:
        raise ValueError("Audio must be WAV format mono with 16kHz sampling rate.")

    rec = KaldiRecognizer(model, wf.getframerate())

    transcript = []
    timestamps = []
    start_time = 0.0

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "")
            if text:
                transcript.append(text)
                duration = len(text.split()) * 0.5
                timestamps.append((start_time, start_time + duration))
                start_time += duration
    
    # Get final result
    final_result = json.loads(rec.FinalResult())
    final_text = final_result.get("text", "")
    if final_text:
        transcript.append(final_text)
        duration = len(final_text.split()) * 0.5
        timestamps.append((start_time, start_time + duration))

    return " ".join(transcript), timestamps

# Transliterate using IndicTrans and Aksharamukha
def transliterate_text(text, target_lang="Tamil"):
    if not text.strip():
        return "No speech detected"
    try:
        # First try direct transliteration if possible
        return transliterate.process("ISO", target_lang, text)
    except:
        # Fall back to Hindi intermediate step
        try:
            indic_translated = UnicodeIndicTransliterator.transliterate(text, "hi", target_lang.lower())
            return transliterate.process("Devanagari", target_lang, indic_translated)
        except Exception as e:
            print(f"❌ Transliteration error: {e}")
            return text  # Return original text if transliteration fails

# Generate SRT subtitles
def generate_srt(transcript, timestamps, output_srt_path):
    subtitles = []
    
    # Handle empty transcript
    if not transcript or not timestamps:
        subtitles.append(srt.Subtitle(
            index=1,
            start=timedelta(seconds=0),
            end=timedelta(seconds=5),
            content="No speech detected"
        ))
    else:
        words = transcript.split()
        word_index = 0
        
        for i, (start, end) in enumerate(timestamps):
            # Create subtitle chunks of 1-3 words
            chunk_size = min(3, len(words) - word_index)
            if chunk_size <= 0:
                break
                
            content = " ".join(words[word_index:word_index+chunk_size])
            subtitles.append(srt.Subtitle(
                index=i + 1,
                start=timedelta(seconds=start),
                end=timedelta(seconds=end),
                content=content
            ))
            
            word_index += chunk_size

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))
    print(f"✅ Subtitles saved to: {output_srt_path}")

# Flask Routes
@app.route("/upload", methods=["POST"])
def upload_video():
    try:
        file = request.files['file']
        lang = request.form.get('language', 'Tamil')
        filename = file.filename
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        audio_path = os.path.splitext(video_path)[0] + ".wav"
        subtitle_filename = os.path.splitext(filename)[0] + ".srt"
        subtitle_path = os.path.join(SUBTITLE_FOLDER, subtitle_filename)

        file.save(video_path)
        print(f"📁 Uploaded: {video_path}")
        print(f"📍 Will save subtitles to: {subtitle_path}")

        # Extract audio and check success
        if not extract_audio(video_path, audio_path):
            return jsonify({"error": "Failed to extract audio from video"}), 500
            
        # Verify the audio file exists
        if not os.path.exists(audio_path):
            return jsonify({"error": "Audio file wasn't created"}), 500
            
        # Verify audio format
        if not verify_audio_format(audio_path):
            return jsonify({"error": "Audio format incorrect, must be 16kHz mono WAV"}), 500

        transcript, timestamps = transcribe_audio(audio_path, VOSK_MODEL_PATH)
        translated_text = transliterate_text(transcript, lang)
        generate_srt(translated_text, timestamps, subtitle_path)

        # Make sure the file was created
        if not os.path.exists(subtitle_path):
            print(f"❌ SRT file not created: {subtitle_path}")
            return jsonify({"error": "Failed to create subtitle file"}), 500

        print(f"✅ Processing complete, SRT file created: {subtitle_filename}")
        
        # Return just the filename, not the full path
        return jsonify({
            "message": "✅ Processing complete", 
            "subtitle": subtitle_filename
        })
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get-subtitles", methods=["GET"])
def get_subtitles():
    subtitle_file = request.args.get("file")
    if not subtitle_file:
        print("❌ No subtitle file specified in request")
        return jsonify({"error": "No file specified"}), 400
        
    file_path = os.path.join(SUBTITLE_FOLDER, subtitle_file)
    print(f"🔍 Looking for subtitle file at: {file_path}")
    
    if os.path.exists(file_path):
        print(f"✅ Sending subtitle file: {file_path}")
        return send_file(file_path, as_attachment=True)
    else:
        print(f"❌ File not found: {file_path}")
        return jsonify({"error": "File not found"}), 404

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    # Print folder information at startup for debugging
    print(f"📂 UPLOAD_FOLDER: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"📂 SUBTITLE_FOLDER: {os.path.abspath(SUBTITLE_FOLDER)}")
    print(f"🚀 Starting Flask server...")
    app.run(debug=True)