"""
Recherche web pour Rem, via DuckDuckGo (package `ddgs`, sans clé API).
Installation : pip install ddgs
"""

from ddgs import DDGS


def search_text(query: str, max_results: int = 5):
    """Résultats web classiques (titre, url, extrait)."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        print("Erreur recherche web (texte) :", e)
        return []


def search_images(query: str, max_results: int = 6):
    """Résultats images (titre, url de la page, url de la miniature)."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.images(query, max_results=max_results))
    except Exception as e:
        print("Erreur recherche web (images) :", e)
        return []


def search_videos(query: str, max_results: int = 4):
    """Résultats vidéos (titre, url, durée...)."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.videos(query, max_results=max_results))
    except Exception as e:
        print("Erreur recherche web (vidéos) :", e)
        return []
