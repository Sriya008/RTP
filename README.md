# 🎥 AI Video Transliteration Tool

An intelligent web-based application that converts **spoken English video content into subtitles in Indian regional languages** selected by the user. The system uses **speech recognition, transliteration, and AI-powered subtitle generation**, delivering downloadable `.srt` files for accurate subtitle sync.

---

## 📌 Features

- 🎙️ Speech-to-text transcription using **Vosk ASR**
- 🌐 Transliteration into 8 Indian languages using **IndicTrans**, **Aksharamukha**, and **Indic NLP**
- 📹 Support for MP4, AVI, MOV, MKV uploads (up to 500MB)
- 🧠 AI-enhanced sentence grouping for better subtitle readability
- 📄 Downloadable `.srt` subtitle file
- 🖥️ Integrated video preview and status-based UI
- 🔐 Auto file cleanup after 24 hours for privacy

---

## 👩‍💻 Tech Stack

| Layer             | Technology                             |
|------------------|-----------------------------------------|
| Frontend         | HTML, CSS, JavaScript (`index1.html`)   |
| Backend          | Python (Flask) - `app1.py`              |
| Speech-to-Text   | Vosk + Kaldi                            |
| Transliteration  | IndicTrans, Aksharamukha, Indic NLP     |
| Video Handling   | MoviePy (FFmpeg)                        |
| Subtitles        | python-srt library                      |

---

## 🛠️ Setup Instructions

### ✅ Prerequisites
- Python 3.8+
- FFmpeg installed and added to PATH
- Git
- Vosk model (`vosk-model-en-us-0.22` downloaded)
- Virtual environment recommended (`testvenv`)

### 🔧 Installation

```bash
# 1. Clone the repo
git clone https://github.com/Sriya008/RTP.git
cd RTP

# 2. Create and activate virtual environment
python -m venv testvenv
testvenv\Scripts\activate    # On Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Ensure FFmpeg is installed
ffmpeg -version

# 5. Run the server
python app1.py
Then open your browser at:
http://127.0.0.1:5001/test

📁 Folder Structure
RTP_Transliterationtool/
│
├── app1.py                # Main Flask backend
├── index1.html            # Frontend (in templates/)
├── vosk-model-en-us-0.22/ # Vosk English model
├── static/videos/         # Processed videos
├── uploads_test/          # Temporary video uploads
├── subtitles_test/        # Generated .srt subtitle files
├── testvenv/              # Python virtual environment
├── .gitignore
└── README.md              # You're here!

🌍 Supported Languages
Tamil (தமிழ்)

Hindi (हिन्दी)

Telugu (తెలుగు)

Malayalam (മലയാളം)

Kannada (ಕನ್ನಡ)

Bengali (বাংলা)

Marathi (मराठी)

Gujarati (ગુજરાતી)

🧑‍🤝‍🧑 Target Audience
Students and educators working with multilingual content

Regional YouTube creators

Accessibility tools for Indian languages

AI-powered subtitling services

🏁 Future Enhancements
🔊 Speaker diarization (multi-speaker detection)

📲 Mobile-responsive frontend

📼 Upload from YouTube URL

🧠 Fine-tuned ASR models for Indian accents

🤝 Contributors
Sriya M. – @Sriya008
Pranuthi @Pranuthi-hub
Sujay @sujay495
Giridhar @giri-23


