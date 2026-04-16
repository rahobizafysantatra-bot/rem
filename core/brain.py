import ollama

# Mémoire de la conversation
historique = []

def demander(message_utilisateur):
    # Ajoute le message de l'utilisateur à l'historique
    historique.append({
        "role": "user",
        "content": message_utilisateur
    })

    # Envoie la conversation à Mistral via Ollama
    reponse = ollama.chat(
        model="mistral:7b",
        messages=historique
    )

    # Récupère le texte de la réponse
    texte_reponse = reponse["message"]["content"]

    # Ajoute la réponse à l'historique
    historique.append({
        "role": "assistant",
        "content": texte_reponse
    })

    return texte_reponse