import base64
import json
import math
import re
import unicodedata
from openai import OpenAI
from .config import get_settings
from .models import KnowledgeItem, Project

PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
PHOTO_MAX_SIZE = 15 * 1024 * 1024
STOPWORDS = {"para", "como", "este", "esta", "esto", "desde", "sobre", "entre", "todo", "toda", "todos", "todas", "pero", "porque", "donde", "cuando", "quiere", "proyecto", "marca", "cliente", "objetivo", "brief", "una", "uno", "unos", "unas", "con", "del", "los", "las", "por", "que", "the", "and", "with", "from"}


def normalized_tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return {token for token in re.findall(r"[a-z0-9]{3,}", normalized) if token not in STOPWORDS}


def index_text(item: KnowledgeItem) -> str:
    return " ".join(filter(None, [item.title, item.source, item.notes, item.tags, item.ai_summary, item.ai_observations]))


def embed_text(text: str) -> list[float] | None:
    settings = get_settings()
    if not settings.openai_api_key or not text.strip():
        return None
    try:
        response = OpenAI(api_key=settings.openai_api_key).embeddings.create(
            model=settings.openai_embedding_model,
            input=text[:24000].replace("\n", " "),
            dimensions=256,
        )
        return response.data[0].embedding
    except Exception:
        return None


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def relevant_matches(
    project: Project,
    items: list[KnowledgeItem],
    item_vectors: dict[str, list[float]] | None = None,
    query_vector: list[float] | None = None,
    limit: int = 8,
) -> list[tuple[KnowledgeItem, int, str]]:
    project_tokens = normalized_tokens(f"{project.name} {project.objective} {project.brief}")
    scored: list[tuple[int, object, KnowledgeItem, str]] = []
    for item in items:
        overlap = project_tokens & normalized_tokens(item.indexed_text or index_text(item))
        lexical = min(1.0, len(overlap) / max(2.0, math.sqrt(max(1, len(project_tokens)))))
        vector = (item_vectors or {}).get(str(item.id))
        semantic = cosine_similarity(query_vector, vector) if query_vector and vector else 0.0
        if not overlap and semantic < 0.35:
            continue
        combined = max(lexical, semantic) if not overlap or not semantic else (0.55 * semantic + 0.45 * lexical)
        reason = f"Coincide en: {', '.join(sorted(overlap)[:5])}" if overlap else "Afinidad semántica con el brief"
        scored.append((round(combined * 100), item.created_at, item, reason))
    scored.sort(key=lambda value: (value[0], value[1]), reverse=True)
    return [(value[2], value[0], value[3]) for value in scored[:limit]]


def relevant_items(project: Project, items: list[KnowledgeItem], limit: int = 5) -> list[KnowledgeItem]:
    return [match[0] for match in relevant_matches(project, items, limit=limit)]


def analyze_photo(data: bytes, content_type: str, title: str, notes: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.openai_api_key:
        summary = notes.strip() or f"Foto incorporada al Radar con el título “{title}”."
        return {
            "ai_summary": summary,
            "ai_observations": "Indexada con el título, lugar, contexto y etiquetas aportados. El análisis automático de lo visible en la imagen se habilita al configurar una API key.",
            "index_status": "indexed",
        }

    try:
        encoded = base64.b64encode(data).decode("ascii")
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_vision_model,
            reasoning={"effort": "none"},
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": f"Analizá esta foto para una biblioteca de inteligencia estratégica. Título: {title}. Contexto aportado: {notes or 'sin contexto'}. Respondé JSON con summary (descripción objetiva y texto visible relevante) y observations (patrones de diseño, comportamiento, tendencias o aprendizajes potenciales; indicá incertidumbre)."},
                {"type": "input_image", "image_url": f"data:{content_type};base64,{encoded}", "detail": "high"},
            ]}],
        )
        raw = response.output_text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
        parsed = json.loads(raw)
        return {"ai_summary": parsed.get("summary", ""), "ai_observations": parsed.get("observations", ""), "index_status": "indexed"}
    except Exception:
        summary = notes.strip() or f"Foto incorporada al Radar con el título “{title}”."
        return {
            "ai_summary": summary,
            "ai_observations": "Indexada con el contexto aportado. El análisis visual con IA está pendiente porque la API no está disponible en este momento.",
            "index_status": "indexed",
        }


def radar_context(items: list[KnowledgeItem]) -> str:
    return "\n\n".join(
        f"RADAR OLIVA — {item.kind.value.upper()}: {item.title}\nFuente: {item.source or 'No indicada'}\nURL: {item.url or 'Foto interna'}\nResumen: {item.ai_summary or item.notes}\nObservaciones: {item.ai_observations}\nEtiquetas: {item.tags}\nContenido indexado: {item.indexed_text[:6000]}"
        for item in items
    )
