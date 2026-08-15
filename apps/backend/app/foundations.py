"""Conocimiento permanente de OLIVA: criterio, no evidencia de un cliente."""

FOUNDATIONAL_REFERENCES = [
    {"author": "Gregory Bateson", "work": "Steps to an Ecology of Mind", "lens": "patrones, contexto y niveles de aprendizaje"},
    {"author": "Tim Brown", "work": "Change by Design", "lens": "deseabilidad, factibilidad y viabilidad"},
    {"author": "John Dewey", "work": "How We Think", "lens": "indagación: dificultad, hipótesis y prueba"},
    {"author": "Daniel Kahneman", "work": "Thinking, Fast and Slow", "lens": "sesgos y controles de juicio"},
    {"author": "Gary Klein", "work": "Sources of Power", "lens": "pericia y reconocimiento de patrones"},
    {"author": "Donella Meadows", "work": "Thinking in Systems", "lens": "bucles, demoras y puntos de intervención"},
    {"author": "Charles S. Peirce", "work": "Escritos sobre pragmatismo y abducción", "lens": "hipótesis explicativas y refutables"},
    {"author": "Michael Polanyi", "work": "The Tacit Dimension", "lens": "conocimiento tácito y práctica experta"},
    {"author": "Donald A. Schön", "work": "The Reflective Practitioner", "lens": "reflexión en la acción"},
    {"author": "Peter M. Senge", "work": "The Fifth Discipline", "lens": "modelos mentales y aprendizaje organizacional"},
    {"author": "Herbert A. Simon", "work": "The Sciences of the Artificial", "lens": "diseño de situaciones preferidas bajo racionalidad limitada"},
    {"author": "Karl E. Weick", "work": "Sensemaking in Organizations", "lens": "construcción de sentido en situaciones ambiguas"},
]

FESTIVAL_CATALOG = [
    {"id": "effie", "name": "Effie Worldwide", "url": "https://effie.org/winners/", "focus": "efectividad, resultados y aprendizaje de negocio"},
    {"id": "cannes", "name": "Cannes Lions", "url": "https://www.canneslions.com/awards", "focus": "creatividad, innovación, craft y transformación"},
    {"id": "dandad", "name": "D&AD", "url": "https://www.dandad.org/awards/", "focus": "excelencia creativa y craft"},
    {"id": "one_show", "name": "The One Show", "url": "https://www.oneclub.org/awards/theoneshow/", "focus": "ideas, diseño y producción"},
    {"id": "clio", "name": "Clio Awards", "url": "https://clios.com/", "focus": "publicidad, entretenimiento y experiencias"},
    {"id": "fiap", "name": "FIAP", "url": "https://www.fiapawards.com/", "focus": "creatividad iberoamericana"},
    {"id": "el_ojo", "name": "El Ojo de Iberoamérica", "url": "https://www.elojodeiberoamerica.com/premio/", "focus": "creatividad y perspectiva latina"},
    {"id": "el_sol", "name": "El Sol", "url": "https://elsolfestival.com/", "focus": "comunicación publicitaria iberoamericana"},
    {"id": "sxsw", "name": "SXSW", "url": "https://sxsw.com/pitch/archive/", "focus": "innovación, tecnología y cultura"},
    {"id": "desachate", "name": "Desachate", "url": "https://desachate.com/", "focus": "creatividad publicitaria uruguaya"},
]

AGENT_CATALOG = [
    {"key": "briefing", "name": "OLIVA Briefing", "stage": "Ingreso", "description": "Normaliza el pedido, separa decisiones tomadas, fuentes, contradicciones y preguntas."},
    {"key": "strategy", "name": "OLIVA Strategy", "stage": "Diagnóstico y estrategia", "description": "Construye el contrabrief, hipótesis, riesgos y tres rutas estratégicas."},
    {"key": "creative_director", "name": "OLIVA Creative Director", "stage": "Desarrollo creativo", "description": "Convierte una ruta aprobada en plataformas creativas y controles de propiedad."},
    {"key": "research", "name": "OLIVA Research", "stage": "Investigación", "description": "Diseña una agenda de investigación y clasifica qué debe verificarse."},
    {"key": "learning_curator", "name": "OLIVA Learning", "stage": "Aprendizaje", "description": "Transforma decisiones y resultados validados en aprendizajes reutilizables."},
]


def foundational_context() -> str:
    return "\n".join(
        f"- {item['author']} · {item['work']}: {item['lens']}."
        for item in FOUNDATIONAL_REFERENCES
    )
