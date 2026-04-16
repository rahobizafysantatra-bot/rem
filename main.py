from core.brain import demander
from core.voice import parler


welcome_message = "Welcome sir Aruchiwa. What can I help you today?"
print(welcome_message)
parler(welcome_message)
print("Jarvis démarré ! (tape 'quitter' pour arrêter)")

while True:
    message = input("Vous : ")
    
    if message.lower() == "quitter":
        break
    
    reponse = demander(message)
    
    print(f"Jarvis : {reponse}")
    
    # 🔊 voix de Jarvis
    parler(reponse)