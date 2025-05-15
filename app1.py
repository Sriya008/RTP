from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
import os
import wave
import json
import srt
import logging
import time
from datetime import timedelta
from moviepy.editor import VideoFileClip
from vosk import Model, KaldiRecognizer, SetLogLevel
import tempfile
import uuid
import re
import shutil
import indic_transliteration
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate
from aksharamukha import transliterate as aksharamukha_transliterate

# Try to import Google Translate for better translation
try:
    from googletrans import Translator
    translator = Translator()
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress Vosk debug messages
SetLogLevel(-1)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB limit
app.config['UPLOAD_FOLDER'] = "uploads_test"
app.config['SUBTITLE_FOLDER'] = "subtitles_test"
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SUBTITLE_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'videos'), exist_ok=True)

# Vosk model path - CHANGE THIS TO YOUR ACTUAL PATH
VOSK_MODEL_PATH = r"C:\Users\Sriya\RTP\vosk-model-en-us-0.22"

# Language configuration with Aksharamukha script mappings
LANGUAGE_CONFIG = {
    "Tamil": {
        "code": "ta", 
        "script": "Tamil",
        "scheme": sanscript.TAMIL,
        "aksharamukha_script": "Tamil"
    },
    "Hindi": {
        "code": "hi", 
        "script": "Devanagari",
        "scheme": sanscript.DEVANAGARI,
        "aksharamukha_script": "Devanagari" 
    },
    "Telugu": {
        "code": "te", 
        "script": "Telugu",
        "scheme": sanscript.TELUGU,
        "aksharamukha_script": "Telugu"
    },
    "Malayalam": {
        "code": "ml", 
        "script": "Malayalam",
        "scheme": sanscript.MALAYALAM,
        "aksharamukha_script": "Malayalam"
    },
    "Kannada": {
        "code": "kn", 
        "script": "Kannada",
        "scheme": sanscript.KANNADA,
        "aksharamukha_script": "Kannada"
    },
    "Bengali": {
        "code": "bn", 
        "script": "Bengali",
        "scheme": sanscript.BENGALI,
        "aksharamukha_script": "Bengali"
    },
    "Marathi": {
        "code": "mr", 
        "script": "Devanagari",
        "scheme": sanscript.DEVANAGARI,
        "aksharamukha_script": "Devanagari"
    },
    "Gujarati": {
        "code": "gu", 
        "script": "Gujarati",
        "scheme": sanscript.GUJARATI,
        "aksharamukha_script": "Gujarati"
    },
    "Punjabi": {
        "code": "pa",
        "script": "Gurmukhi",
        "scheme": None,  # No direct mapping in sanscript
        "aksharamukha_script": "Gurmukhi"
    },
    "Odia": {
        "code": "or",
        "script": "Oriya",
        "scheme": None,  # No direct mapping in sanscript
        "aksharamukha_script": "Oriya"
    },
    "Sanskrit": {
        "code": "sa",
        "script": "Devanagari",
        "scheme": sanscript.DEVANAGARI,
        "aksharamukha_script": "Devanagari"
    }
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def clean_filename(filename):
    # Keep only alphanumeric, dots, underscores and hyphens
    return re.sub(r'[^a-zA-Z0-9._-]', '', filename)

def extract_audio(video_path, output_audio_path):
    try:
        logger.info(f"Extracting audio from {video_path}")
        video = VideoFileClip(video_path)
        
        if video.audio is None:
            raise ValueError("No audio track in video file")
            
        audio = video.audio
        audio.write_audiofile(
            output_audio_path,
            fps=16000,
            nbytes=2,
            codec='pcm_s16le',
            ffmpeg_params=["-ac", "1"]
        )
        return True
    except Exception as e:
        logger.error(f"Audio extraction error: {e}")
        return False

def transcribe_audio(audio_path):
    try:
        model = Model(VOSK_MODEL_PATH)
        
        with wave.open(audio_path, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                raise ValueError("Audio must be WAV format mono with 16kHz sampling rate")
                
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)
            
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if 'result' in result:
                        results.extend(result['result'])
            
            final_result = json.loads(rec.FinalResult())
            if 'result' in final_result:
                results.extend(final_result['result'])
                
        if not results:
            return "No speech detected", []
            
        words_with_time = [(item['word'], float(item['start']), float(item['end'])) 
                         for item in results]
        
        # Group words into sentences more intelligently
        segments = []
        current_sentence = []
        current_start = None
        sentence_end_markers = {'.', '!', '?'}
        
        for i, (word, start, end) in enumerate(words_with_time):
            if current_start is None:
                current_start = start
                
            current_sentence.append(word)
            
            # End sentence on punctuation or when it gets too long
            if (word[-1] in sentence_end_markers or 
                len(current_sentence) >= 15 or 
                i == len(words_with_time) - 1):
                
                sentence_text = ' '.join(current_sentence)
                segments.append((sentence_text, current_start, end))
                current_sentence = []
                current_start = None
                
        if current_sentence:  # Add any remaining words
            segments.append((' '.join(current_sentence), 
                           current_start or words_with_time[0][1], 
                           words_with_time[-1][2]))
            
        transcript = ' '.join(segment[0] for segment in segments)
        timestamps = [(segment[1], segment[2]) for segment in segments]
        
        return transcript, segments  # Return segments instead of just timestamps
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return f"Error: {str(e)}", []

def translate_text(text, target_lang_code):
    """Attempt to translate text using Google Translate if available"""
    if not GOOGLE_TRANSLATE_AVAILABLE:
        return None
        
    try:
        translation = translator.translate(text, dest=target_lang_code)
        return translation.text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None

def preprocess_text_for_transliteration(text):
    """Prepare text for better transliteration results"""
    if not text or not text.strip():
        return "No speech detected"
    
    # Basic text normalization
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Add appropriate spacing for punctuation
    text = re.sub(r'([.,!?;:])', r' \1 ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Handle common English sounds that need special mapping
    # These replacements help create better phonetic mappings for Indian languages
    phonetic_mappings = {
        'sh': 'ś',     # For sounds like "sh" in "shine"
        'ch': 'c',     # For sounds like "ch" in "charge"
        'th': 'th',    # Keep as is, will be handled by Aksharamukha
        'ph': 'ph',    # Keep as is for proper phonetic mapping
        'ee': 'ī',     # Long "ee" sound
        'oo': 'ū',     # Long "oo" sound
        'aa': 'ā',     # Long "aa" sound
        'ai': 'ai',    # For diphthongs
        'au': 'au',    # For diphthongs
        'ay': 'ai',    # Alternative spelling for "ai" sound
    }
    
    for eng, ind in phonetic_mappings.items():
        text = text.replace(eng, ind)
    
    return text

def transliterate_text(text, target_lang):
    """Multi-layered approach: First try translation, then transliteration"""
    if not text or not text.strip():
        return "No speech detected"
    
    lang_code = LANGUAGE_CONFIG[target_lang]["code"]
    
    # Step 1: Try translation first (semantic preservation)
    if GOOGLE_TRANSLATE_AVAILABLE:
        try:
            translated = translate_text(text, lang_code)
            if translated:
                logger.info(f"Translation successful: {translated[:50]}...")
                return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
    
    # Step 2: Fallback to transliteration (phonetic preservation)
    try:
        logger.info(f"Transliterating to {target_lang}: {text[:50]}...")
        
        # Preprocess text for better transliteration
        processed_text = preprocess_text_for_transliteration(text)
        
        # Primary method: Aksharamukha (superior for Indic scripts)
        target_script = LANGUAGE_CONFIG[target_lang]["aksharamukha_script"]
        
        # Use Aksharamukha's comprehensive transliteration system
        transliterated = aksharamukha_transliterate.process(
            "ISO", 
            target_script,
            processed_text,
            nativize=True  # Enable intelligent nativization for better results
        )
        
        logger.info(f"Aksharamukha transliteration successful: {transliterated[:50]}...")
        return transliterated
        
    except Exception as e:
        logger.error(f"Aksharamukha transliteration failed: {e}")
        
        # Try fallback methods if primary fails
        try:
            # Fallback 1: indic_transliteration if available for this language
            if LANGUAGE_CONFIG[target_lang]["scheme"]:
                scheme = LANGUAGE_CONFIG[target_lang]["scheme"]
                transliterated = transliterate(processed_text, sanscript.IAST, scheme)
                logger.info(f"Fallback to indic_transliteration successful")
                return transliterated
        except Exception as e2:
            logger.error(f"indic_transliteration fallback failed: {e2}")
            
            # Last resort: return original text
            logger.warning(f"All transliteration methods failed. Returning original text")
            return text

def post_process_transliteration(text, target_lang):
    """Apply language-specific adjustments to improve transliteration quality"""
    if not text or text == "No speech detected":
        return text
        
    # Apply language-specific post-processing
    if target_lang == "Tamil":
        # Tamil-specific fixes
        text = text.replace('க்ஷ', 'க்ஷ')  # Fix for specific Tamil conjunct
        
    elif target_lang == "Telugu":
        # Telugu-specific fixes
        text = text.replace('్న్', '్న')  # Fix common Telugu conjunct issue
        
    elif target_lang in ["Hindi", "Marathi", "Sanskrit"]:
        # Devanagari script fixes
        text = text.replace('त्र्', 'त्र')  # Fix for त्र conjunct
        
    return text

def generate_srt(transcript_segments, output_path, target_lang):
    """Generate SRT file with translated/transliterated content"""
    try:
        subtitles = []
        
        if not transcript_segments:
            subtitles.append(srt.Subtitle(
                index=1,
                start=timedelta(seconds=0),
                end=timedelta(seconds=5),
                content="No speech detected"
            ))
        else:
            for i, (text, start, end) in enumerate(transcript_segments):
                # Process each segment individually
                if GOOGLE_TRANSLATE_AVAILABLE:
                    # Try translation first for better semantic preservation
                    lang_code = LANGUAGE_CONFIG[target_lang]["code"]
                    translated = translate_text(text, lang_code)
                    if translated:
                        subtitle_text = translated
                    else:
                        subtitle_text = transliterate_text(text, target_lang)
                else:
                    subtitle_text = transliterate_text(text, target_lang)
                
                # Apply post-processing
                subtitle_text = post_process_transliteration(subtitle_text, target_lang)
                
                # Set reasonable duration (min 1 sec, max 7 sec)
                duration = end - start
                if duration < 1.0:
                    end = start + 1.0
                elif duration > 7.0:
                    end = start + 7.0
                
                # Create subtitle entry
                subtitles.append(srt.Subtitle(
                    index=i + 1,
                    start=timedelta(seconds=start),
                    end=timedelta(seconds=end),
                    content=subtitle_text
                ))
        
        # Write subtitles to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt.compose(subtitles))
            
        # Also create a VTT file for better browser compatibility
        vtt_output_path = output_path.replace('.srt', '.vtt')
        create_vtt_from_srt(subtitles, vtt_output_path)
            
        return True
    except Exception as e:
        logger.error(f"SRT generation error: {e}")
        return False

def create_vtt_from_srt(subtitles, output_path):
    """Convert SRT format subtitles to VTT format for better web compatibility"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            
            for subtitle in subtitles:
                # Format timestamps for VTT (HH:MM:SS.mmm)
                start = format_timestamp(subtitle.start.total_seconds())
                end = format_timestamp(subtitle.end.total_seconds())
                
                # Write cue
                f.write(f"{start} --> {end}\n")
                f.write(f"{subtitle.content}\n\n")
                
        return True
    except Exception as e:
        logger.error(f"VTT conversion error: {e}")
        return False

def format_timestamp(seconds):
    """Format seconds to VTT timestamp format HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')

@app.route("/")
def index():
    return redirect(url_for('test_index'))

@app.route("/test")
def test_index():
    return render_template("index1.html")

@app.route("/test/upload", methods=["POST"])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    lang = request.form.get('language', 'Tamil')
    if lang not in LANGUAGE_CONFIG:
        return jsonify({"error": "Invalid language selection"}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
        
    try:
        # Generate unique filename
        clean_name = clean_filename(file.filename)
        unique_id = uuid.uuid4().hex
        base_name = f"{unique_id}_{clean_name}"
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], base_name)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}.wav")
        subtitle_path = os.path.join(app.config['SUBTITLE_FOLDER'], f"{unique_id}.srt")
        vtt_path = os.path.join(app.config['SUBTITLE_FOLDER'], f"{unique_id}.vtt")
        
        # Path for static serving of video
        static_video_path = os.path.join('static', 'videos', base_name)
        
        # Save original file
        file.save(video_path)
        
        # Create a copy for static serving
        shutil.copy2(video_path, static_video_path)
        
        # Process video
        logger.info(f"Processing video {base_name} for {lang} transliteration")
        
        if not extract_audio(video_path, audio_path):
            raise Exception("Audio extraction failed")
            
        logger.info(f"Audio extracted successfully, starting transcription")
        transcript, transcript_segments = transcribe_audio(audio_path)
        if not transcript or transcript.startswith("Error:"):
            raise Exception(f"Transcription failed: {transcript}")
            
        logger.info(f"Transcription successful, generating subtitles for {lang}")
        if not generate_srt(transcript_segments, subtitle_path, lang):
            raise Exception("SRT generation failed")
            
        # Clean up audio file
        try:
            os.remove(audio_path)
        except:
            pass
            
        logger.info(f"Processing complete for {base_name}")
        return jsonify({
            "message": "Processing complete",
            "subtitle": f"{unique_id}.srt",
            "vtt": f"{unique_id}.vtt",
            "video": f"videos/{base_name}",
            "language": lang
        })
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        # Clean up any partial files
        for path in [video_path, audio_path, subtitle_path, vtt_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except:
                pass
        try:
            if os.path.exists(static_video_path):
                os.remove(static_video_path)
        except:
            pass
        return jsonify({"error": str(e)}), 500

@app.route("/test/get-subtitles")
def get_subtitles():
    subtitle_file = request.args.get("file")
    if not subtitle_file or not re.match(r'^[a-f0-9]{32}\.(srt|vtt)$', subtitle_file):
        return jsonify({"error": "Invalid filename"}), 400
        
    file_path = os.path.join(app.config['SUBTITLE_FOLDER'], subtitle_file)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    # Set appropriate content type based on file extension
    content_type = 'text/vtt' if subtitle_file.endswith('.vtt') else 'application/x-subrip'
    
    # Serve the file with the correct MIME type for browser compatibility
    return send_file(
        file_path, 
        as_attachment=True if 'download' in request.args else False,
        mimetype=content_type
    )

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_file(os.path.join('static', filename))

def cleanup_old_files():
    """Clean up files older than 24 hours"""
    try:
        now = time.time()
        for folder in [app.config['UPLOAD_FOLDER'], app.config['SUBTITLE_FOLDER'], 
                      os.path.join('static', 'videos')]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    if now - os.path.getmtime(file_path) > a86400:  # 24 hours
                        os.remove(file_path)
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

@app.route("/test/languages")
def get_languages():
    """Return available languages for the frontend"""
    return jsonify({
        "languages": list(LANGUAGE_CONFIG.keys())
    })

if __name__ == "__main__":
    logger.info(f"Starting test server on port 5001")
    # Install the missing packages
    try:
        import pip
        pip.main(['install', 'googletrans==4.0.0-rc1'])
        logger.info("Installed Google Translate package")
    except:
        logger.warning("Could not install Google Translate package. Continuing without translation.")
    app.run(host='0.0.0.0', port=5001, debug=True)