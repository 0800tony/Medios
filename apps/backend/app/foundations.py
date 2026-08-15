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

# Referencias declaradas por OLIVA. Son lentes de trabajo, no imitaciones de personas
# ni garantía de que una idea provenga de un autor específico.
CREATIVE_REFERENCE_LENSES = [
    {"names": "Ramiro Agulla, Carlos Baccetti, Martín Mercado, Chacho Puebla, Leandro Raposo, Joaquín Cubría, Fernando Vega Olmos, Diego Medvedocky, Hernán Ponce", "lens": "observación cultural, idea simple y recordable, giro publicitario y construcción de campañas populares sin subestimar a la audiencia"},
    {"names": "David Droga, Susan Credle, Debbi Vandeven, Anselmo Ramos, Pancho Cassis, Juan Cabral, Ricardo Silvestre, Fernando Machado", "lens": "ideas con punto de vista, craft subordinado al concepto, valentía relevante y sistemas de campaña que viven en medios distintos"},
    {"names": "David Ogilvy, Rory Sutherland, Martin Lindstrom, Paco Underhill, Mark Ritson, Richard Shotton, Gerald Zaltman, Douglas Holt, Annie Pettit", "lens": "distintividad de marca, comportamiento real, contexto de compra, cultura, memoria y eficacia antes que adjetivos"},
    {"names": "Michael Porter, Philip Kotler, Al Ries, Byron Sharp, Solomon, Graves", "lens": "elección competitiva, posicionamiento, disponibilidad mental y física, segmentación útil y disciplina comercial"},
    {"names": "Claudio Invernizzi, Nacho Vallejo, Esteban Barreiro, Mario Taglioretti, Mauricio Minchilli, Gabriel Román, Diego Lev, Martín Carrier, Dominique Sarries, Emir Cámara, Álvaro Moré, Carina Silva, Chelo Waintraub, Bruno Petcho, Marco Caltieri, Leonel Delfino, Toto Barrera, Bicho Orlando, Gabriel Lista, Diego Lazcano, Gonzalo López Baliñas, Rafael Bartaburu Trujillo", "lens": "lectura local, oficio uruguayo, cercanía cultural, realidad de medios y producción regional"},
]


def foundational_context() -> str:
    return "\n".join(
        f"- {item['author']} · {item['work']}: {item['lens']}."
        for item in FOUNDATIONAL_REFERENCES
    )


def creative_reference_context() -> str:
    return "\n".join(f"- {item['names']}: {item['lens']}." for item in CREATIVE_REFERENCE_LENSES)
