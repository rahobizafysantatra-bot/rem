from core.brain import demander

print("Jarvis démarré ! (tape 'quitter' pour arrêter)")

while True:
    message = input("Vous : ")
    
    if message.lower() == "quitter":
        break
    
    reponse = demander(message)
    print(f"Jarvis : {reponse}")