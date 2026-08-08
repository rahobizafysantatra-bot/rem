import ollama

# Prompt système
system = """
You are REM, an advanced AI assistant inspired by Iron Man's JARVIS.

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
- When sharing code, always wrap it in triple backticks with the language
  name right after the first backticks (e.g. ```python ... ```), so it can
  be displayed as a proper code block.

You exist to assist the user like a high-level personal AI system.
"""


def demander(message_utilisateur, historique):
    """
    historique : liste de messages au format Ollama (role/content) propre
    à UNE conversation. Elle est modifiée sur place (on y ajoute le message
    utilisateur puis la réponse), ce qui permet d'avoir un historique
    différent par conversation plutôt qu'une seule mémoire globale partagée.
    """
    historique.append({
        "role": "user",
        "content": message_utilisateur
    })

    reponse = ollama.chat(
        model="qwen2.5:3b",
        messages=[
            {
                "role": "system",
                "content": system
            }
        ] + historique
    )

    texte_reponse = reponse["message"]["content"]

    historique.append({
        "role": "assistant",
        "content": texte_reponse
    })

    return texte_reponse