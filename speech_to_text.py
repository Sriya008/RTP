import wave
import json
from vosk import Model, KaldiRecognizer

def transcribe_audio(audio_path, model_path):
    """Converts audio speech to text using Vosk."""
    model = Model(model_path)
    wf = wave.open(audio_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())

    transcript = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            transcript.append(result["text"])

    return " ".join(transcript)

# Example usage
# text = transcribe_audio("output_audio.wav", "vosk-model-en-us-0.22")
# print(text)
