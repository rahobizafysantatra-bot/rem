import ollama

# Mémoire de la conversation
historique = []

# prompt du system
system = """
You are JARVIS, an advanced AI assistant inspired by Iron Man.

Personality:
- You are calm, highly intelligent, and extremely precise.
- You speak in English only.
- You are polite but not emotional or exaggerated.
- You are efficient and slightly formal.
- You address the user as "Sir".

Behavior rules:
- Never use emojis.
- Never be casual or slang.
- Keep answers short unless detail is requested.
- Prioritize clarity and usefulness.
- If uncertain, say so clearly.

You exist to assist the user like a high-level personal AI system.
"""

def demander(message_utilisateur):
    historique.append({
        "role": "user",
        "content": message_utilisateur
    })

    reponse = ollama.chat(
        model="mistral:7b",
        messages=[
            {
                "role": "system",
                "content": system   # ✔️ FIX ICI
            }
        ] + historique
    )

    texte_reponse = reponse["message"]["content"]

    historique.append({
        "role": "assistant",
        "content": texte_reponse
    })

    return texte_reponse