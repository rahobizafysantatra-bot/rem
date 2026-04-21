from core.brain import demander
from core.voice import parler
from core.audio import ecouter

welcome_message = "Welcome sir. Systems online. How can I assist you today?"
print(welcome_message)
parler(welcome_message)

while True:
    texte = ecouter()
    
    if not texte:
        continue
    
    if "goodbye" in texte.lower() or "shut down" in texte.lower():
        parler("Goodbye sir. Shutting down.")
        break
    
    reponse = demander(texte)
    print(f"Jarvis : {reponse}")
    parler(reponse)
    # 🔊 voix de Jarvis
    parler(reponse)