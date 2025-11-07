import os
import requests
import logging

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY não configurada no .env")

import re

STOPWORDS = {
    "de", "da", "do", "dos", "das", "um", "uma", "uns", "umas",
    "a", "o", "os", "as", "em", "no", "na", "nos", "nas",
    "para", "por", "com", "que", "se", "sobre", "ao", "à",
    "the", "is", "at", "which", "on", "and", "of", "to", "in"
}

def extract_keywords(text: str, max_keywords: int = 5) -> str:
    words = re.findall(r"\b\w+\b", text.lower())
    keywords = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return " ".join(keywords[:max_keywords]) if keywords else text

def _search_youtube(query: str, max_results: int = 3):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "key": YOUTUBE_API_KEY,
        "maxResults": max_results,
        "type": "video"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        results.append({
            "title": snippet["title"],
            "video_id": video_id,
            "iframe_url": f"https://www.youtube.com/embed/{video_id}",
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "channel": snippet["channelTitle"],
            "published_at": snippet["publishedAt"]
        })
        logger.info(f"results: {results}")
    return results


def run_web_agent(question: str) -> dict:
    logger.info("🔍 [WebAgent] Buscando no YouTube: %s", question)
    try:
        query = extract_keywords(question)
        logger.info("🔎 [WebAgent] Query otimizada: %s", query)

        videos = _search_youtube(query, max_results=3)
        if not videos:
            return {
                "reply": f"🤔 Hmm, não encontrei vídeos sobre '{query}' no YouTube. Tente usar palavras-chave diferentes!\n\n💡 Dica: Seja mais específico, por exemplo:\n- 'Troca de óleo do motor'\n- 'Alinhamento de direção passo a passo'\n- 'Como fazer balanceamento de rodas'", 
                "videos": []
            }

        video_count = len(videos)
        video_word = "vídeo" if video_count == 1 else "vídeos"
        reply = f"🎥 Encontrei {video_count} {video_word} que podem te ajudar com '{query}'!\n\n👇 Confira as opções abaixo:"
        
        return {"reply": reply, "videos": videos}

    except requests.exceptions.HTTPError as e:
        logger.error("❌ [WebAgent] Erro HTTP ao buscar no YouTube: %s", str(e), exc_info=True)
        if "403" in str(e):
            return {"reply": "🔑 A chave da API do YouTube está inválida ou sem permissões. Entre em contato com o suporte.", "videos": []}
        elif "429" in str(e):
            return {"reply": "⏱️ Ops! Atingimos o limite de buscas no YouTube por hoje. Tente novamente mais tarde.", "videos": []}
        else:
            return {"reply": f"😕 Tive um problema ao buscar no YouTube. Código: {e.response.status_code if hasattr(e, 'response') else 'desconhecido'}", "videos": []}
    except requests.exceptions.ConnectionError:
        logger.error("❌ [WebAgent] Erro de conexão com YouTube", exc_info=True)
        return {"reply": "🌐 Não consegui conectar ao YouTube. Verifique sua conexão com a internet.", "videos": []}
    except Exception as e:
        logger.error("❌ [WebAgent] Erro inesperado: %s", str(e), exc_info=True)
        return {"reply": "😅 Ops! Algo deu errado ao buscar vídeos. Tente novamente ou reformule sua busca.", "videos": []}
