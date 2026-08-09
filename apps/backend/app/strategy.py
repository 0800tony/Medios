import json
from openai import OpenAI
from .config import get_settings
from .models import Project

SYSTEM_PROMPT = """Sos OLIVA Strategy, Director de Planeamiento Estratégico Senior. Tu tarea es comprender el problema antes de proponer comunicación. Separá hechos, evidencia, percepciones e hipótesis. Buscá contradicciones, no confundas síntomas con causas e intentá refutar cada hipótesis. Si falta evidencia, decilo. Respondé exclusivamente JSON con: diagnosis, evidence, hypotheses, contradictions, strategic_question, confidence."""


def analyze(project: Project, document_text: str, client_context: str = "") -> dict[str, str]:
    settings = get_settings()
    context = (
        f"Proyecto: {project.name}\n"
        f"Cliente:\n{client_context or 'Sin contexto de cliente'}\n"
        f"Objetivo declarado: {project.objective}\n"
        f"Brief: {project.brief}\n"
        f"Fuentes disponibles:\n{document_text[:70000]}"
    )
    if settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": context}],
            temperature=0.2,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        data["model_used"] = settings.openai_model
        return data

    has_docs = bool(document_text.strip())
    return {
        "diagnosis": "El desafío declarado necesita validarse contra comportamiento, contexto de negocio y evidencia de las personas antes de convertirse en un problema de comunicación.",
        "evidence": ("Se incorporaron documentos al análisis inicial." if has_docs else "No se incorporaron documentos; la evidencia disponible se limita al brief y al objetivo declarado."),
        "hypotheses": "Hipótesis inicial: existe una brecha entre la percepción interna del problema y las motivaciones reales de las personas. Debe contrastarse con investigación.",
        "contradictions": "Aún no hay evidencia suficiente para identificar contradicciones robustas. La ausencia de datos es, por ahora, la principal limitación.",
        "strategic_question": "¿Qué comportamiento concreto debe cambiar, en quién, y qué evidencia demuestra hoy la barrera que lo impide?",
        "confidence": "baja" if not has_docs else "media",
        "model_used": "OLIVA Strategy — modo local",
    }
