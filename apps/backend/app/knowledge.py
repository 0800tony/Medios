import base64
import json
import re
import unicodedata
from openai import OpenAI
from .config import get_settings
from .models import KnowledgeItem, Project

PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
PHOTO_MAX_SIZE = 15 * 1024 * 1024
STOPWORDS = {"para", "como", "este", "esta", "esto", "desde", "sobre", "entre", "todo", "toda", "todos", "todas", "pero", "porque", "donde", "cuando", "quiere", "proyecto", "marca", "cliente", "objetivo", "brief", "the", "and", "with", "from"}


def normalized_tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return {token for token in re.findall(r"[a-z0-9]{3,}", normalized) if token not in STOPWORDS}


def index_text(item: KnowledgeItem) -> str:
    return " ".join(filter(None, [item.title, item.source, item.notes, item.tags, item.ai_summary, item.ai_observations]))


def relevant_items(project: Project, items: list[KnowledgeItem], limit: int = 5) -> list[KnowledgeItem]:
    project_tokens = normalized_tokens(f"{project.name} {project.objective} {project.brief}")
    scored = []
    for item in items:
        overlap = project_tokens & normalized_tokens(item.indexed_text or index_text(item))
        if overlap:
            scored.append((len(overlap), item.created_at, item))
    scored.sort(key=lambda value: (value[0], value[1]), reverse=True)
    return [value[2] for value in scored[:limit]]


def analyze_photo(data: bytes, content_type: str, title: str, notes: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.openai_api_key:
        summary = notes.strip() or "Foto guardada sin análisis automático. Agregá contexto para mejorar su recuperación."
        return {"ai_summary": summary, "ai_observations": "Pendiente de análisis visual con IA.", "index_status": "manual"}

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


def radar_context(items: list[KnowledgeItem]) -> str:
    return "\n\n".join(
        f"RADAR OLIVA — {item.kind.value.upper()}: {item.title}\nFuente: {item.source or 'No indicada'}\nURL: {item.url or 'Foto interna'}\nResumen: {item.ai_summary or item.notes}\nObservaciones: {item.ai_observations}\nEtiquetas: {item.tags}"
        for item in items
    )
