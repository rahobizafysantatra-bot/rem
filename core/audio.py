import whisper
import sounddevice as sd
import numpy as np

# Charge le modèle Whisper (se télécharge automatiquement la première fois)
model = whisper.load_model("base")

DUREE = 5        # secondes d'enregistrement
SAMPLE_RATE = 16000  # fréquence requise par Whisper

def ecouter():
    print("🎙️ Listening...")
    
    # Enregistre le micro pendant DUREE secondes
    audio = sd.rec(
        int(DUREE * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )
    sd.wait()  # Attend la fin de l'enregistrement
    
    # Convertit en format Whisper
    audio = audio.flatten()
    
    # Transcrit l'audio en texte
    result = model.transcribe(audio, language="en")
    
    texte = result["text"].strip()
    print(f"You said : {texte}")
    
    return texte