import base64,json
from pathlib import Path
from .config import get_settings
from .documents import extract_text
from .strategy import response_text,responses_payload,responses_text
from .foundations import creative_reference_context
FESTIVAL_DOMAINS=["canneslions.com","dandad.org","oneclub.org","clios.com","effie.org","fiapawards.com","elojodeiberoamerica.com","elsolfestival.com","sxsw.com","desachate.com","circulopublicidad.com"]
MARKET_RESEARCH_DOMAINS=[
    "kantar.com", "nielseniq.com", "ipsos.com", "gk.com", "euromonitor.com",
    "lanacion.com.ar", "clarin.com", "cronista.com", "ambito.com", "infobae.com",
    "apertura.com", "mercado.com.ar", "iprofesional.com", "adlatina.com",
    "marketingdirecto.com", "reddit.com",
]
SCORE_KEYS=["estrategia","verdad_humana","rol_de_marca","apropiabilidad","originalidad","claridad","fertilidad","coherencia","adecuacion_al_medio","viabilidad"]

AGENT_PROMPT="""Sos un agente especializado de OLIVA Intelligence. Trabajá con trazabilidad: separá hechos, inferencias, hipótesis y faltantes. No inventes resultados, antecedentes ni fuentes. La salida debe ser JSON válido, accionable y apto para aprobación humana. Si recibís lentes de referencia OLIVA, usalos como criterios de evaluación y no como estilos a imitar ni como atribución de ideas a personas."""
CREATIVE_DIRECTION_PROMPT="""Sos OLIVA Creative Director. Trabajá exclusivamente sobre la estrategia y ruta aprobadas. Antes de proponer, controlá estrategia, marca y propiedad: si la idea serviría igual para cualquier marca, marcala débil y reformulala. Usá los lentes de referencia OLIVA como criterios, nunca como una imitación de una persona ni atribución de autoría. Devolvé JSON con desafio_creativo, efecto_buscado, base_aprobada, territorios (exactamente 3), recomendacion y sistema_creativo. Cada territorio debe incluir id, nombre, tension, idea_central, rol_de_marca, tipo_de_campana, estilo, tono, medios, propiedad, riesgos_y_cliches y control. No escribas piezas finales ni inventes evidencia."""
CREATIVE_TABLE_PROMPT="""Sos la Mesa Creativa OLIVA. Trabajás sobre una estrategia, una plataforma elegida y un plan ya existentes. No reescribas la estrategia, no inventes información y no imites a personas reales. Con los lentes OLIVA como criterios, devolvé JSON con intervenciones (exactamente cuatro objetos: rol, acuerdo, objecion, aporte_concreto, prueba_de_propiedad) para Estrategia, Dirección Creativa, Dirección de Arte y Producción; y un cierre con mantener, cambiar, probar y no_hacer. La pregunta del equipo puede abrir una alternativa, pero nunca elimina ni recalcula el trabajo aprobado."""


def model_for_agent(settings, agent_key: str) -> str:
    """Asignación explícita y auditable de modelo para cada agente OLIVA."""
    if agent_key == "strategy":
        return settings.openai_strategy_model
    if agent_key == "creative_director":
        return settings.openai_creative_model
    return settings.openai_operations_model

def sources_from_response(body:dict)->list[dict[str,str]]:
    sources=[];seen=set()
    for output in body.get("output",[]):
        for source in (output.get("action") or {}).get("sources",[]):
            url=source.get("url","")
            if url and url not in seen:
                seen.add(url);sources.append({"title":source.get("title") or url,"url":url})
        for content in output.get("content",[]):
            for source in content.get("annotations",[]):
                url=source.get("url","")
                if source.get("type")=="url_citation" and url and url not in seen:
                    seen.add(url);sources.append({"title":source.get("title") or url,"url":url})
    return sources

def project_web_research(project_name:str, objective:str, query:str, domains:list[str] | None = None)->tuple[str,list[dict[str,str]],str]:
    s=get_settings()
    if not s.openai_api_key:
        return "La búsqueda web se habilita al configurar OPENAI_API_KEY. Mientras tanto podés agregar enlaces manualmente.",[],"modo local"
    prompt=(
        "Investigá información pública relevante para un caso de estrategia publicitaria. "
        "Separá datos comprobables, perspectivas periodísticas y conversación/foros (estos últimos nunca son evidencia concluyente). "
        "Priorizá estudios de investigación de mercado, suplementos empresariales argentinos y medios especializados. "
        "No inventes cifras. Devolvé una síntesis concisa con hallazgos, contradicciones y datos que aún deban validarse. "
        f"Proyecto: {project_name}. Objetivo: {objective}. Foco solicitado: {query}."
    )
    allowed_domains = list(dict.fromkeys(domain.strip().lower() for domain in (domains or MARKET_RESEARCH_DOMAINS) if domain and domain.strip()))[:90] or MARKET_RESEARCH_DOMAINS
    try:
        body=responses_payload({
            "model":s.openai_search_model,
            "reasoning":{"effort":"low"},
            "tools":[{"type":"web_search","search_context_size":"high","filters":{"allowed_domains":allowed_domains}}],
            "tool_choice":"required",
            "include":["web_search_call.action.sources"],
            "input":prompt,
        })
        return response_text(body),sources_from_response(body),body.get("model",s.openai_search_model)
    except Exception:
        return "La IA web no está disponible en este momento. Podés continuar cargando enlaces y evidencia; OLIVA los integrará cuando la cuota de API esté habilitada.",[],"modo local · API no disponible"

def festival_research(query:str)->tuple[str,list[dict[str,str]],str]:
    s=get_settings()
    if not s.openai_api_key:return "La búsqueda automática requiere configurar OPENAI_API_KEY. Podés guardar enlaces manualmente.",[],"modo local"
    try:
        b=responses_payload({"model":s.openai_search_model,"tools":[{"type":"web_search","filters":{"allowed_domains":FESTIVAL_DOMAINS},"search_context_size":"high"}],"tool_choice":"required","include":["web_search_call.action.sources"],"input":f"Buscá casos premiados o finalistas relevantes para: {query}. Consultá solo archivos oficiales de Effie, Cannes Lions, D&AD, The One Show, Clio, FIAP, El Ojo de Iberoamérica, El Sol, SXSW y Desachate/Círculo Uruguayo. Para cada hallazgo distinguí claramente premio, año, categoría, resultado reportado y aprendizaje transferible. No inventes datos ni atribuyas resultados no publicados. Citá las fuentes."})
        return response_text(b),sources_from_response(b),b.get("model",s.openai_search_model)
    except Exception:
        return "La búsqueda automática de festivales no está disponible temporalmente. El catálogo oficial permanece disponible y podés incorporar enlaces manuales.",[],"modo local · API no disponible"


def local_agent_output(agent_key: str, project_name: str, brief: dict, strategy: dict, decision: dict, memory: dict, learning: list[dict], instruction: str) -> dict:
    request = brief.get("request", "") or instruction or "Pedido aún no documentado"
    route = decision.get("route_key", "sin ruta aprobada").replace("_", " ")
    if agent_key == "briefing":
        return {"tipo": "normalización", "pedido_textual": request, "pedido_interpretado": brief.get("business_context") or "El pedido debe traducirse a una situación de negocio, conducta y decisión.", "decisiones_tomadas": [value for value in [brief.get("territory"), brief.get("deadline"), brief.get("restrictions")] if value], "contradicciones_a_revisar": ["No asumir que el pedido comunicacional es la causa del problema.", "Separar disponibilidad, precio, producto y percepción antes de producir piezas."], "siguiente_paso": "Completar el brief y contrastar las hipótesis con fuentes diferenciadas."}
    if agent_key == "research":
        return {"tipo": "agenda de investigación", "pregunta": instruction or f"¿Qué debe verificarse antes de decidir la ruta de {project_name}?", "prioridades": ["Conducta y barrera del público prioritario.", "Oferta, precio, distribución y competidores reales.", "Aprendizajes propios y casos externos comparables."], "metodo": ["Relevar observación y conversaciones de canal/usuarios.", "Buscar estudios y publicaciones de terceros, diferenciando evidencia de señales.", "Registrar fuente, fecha, alcance y límite de cada hallazgo."], "criterio_de_salida": "Contar con una aproximación documentada suficiente para decidir un piloto reversible."}
    if agent_key == "strategy":
        return {"tipo": "orientación estratégica", "estado": "usar análisis estructurado", "mensaje": "El contrabrief de 32 apartados se genera desde el expediente para preservar fuentes, versiones y tres rutas comparables.", "siguiente_paso": "Abrir el proyecto, completar el brief y ejecutar OLIVA Strategy desde el expediente."}
    if agent_key == "creative_director":
        if not decision:
            return {"tipo": "desarrollo creativo", "estado": "bloqueado", "motivo": "No hay una ruta estratégica aprobada. Solo corresponde explorar preguntas, no recomendar una plataforma final.", "siguiente_paso": "Elegir y aprobar una ruta estratégica."}
        core = strategy.get(decision.get("route_key"), {}) if isinstance(strategy, dict) else {}
        hypothesis = core.get("hipotesis", "La ruta aprobada debe hacerse concreta.") if isinstance(core, dict) else str(core)
        return {"tipo": "plataformas creativas exploratorias", "base_aprobada": {"ruta": route, "fundamento": decision.get("rationale", ""), "plan": decision.get("launch_plan", "")}, "desafio_creativo": f"Hacer visible la decisión estratégica de {project_name} sin convertirla en una pieza genérica.", "rutas": [{"nombre": "La prueba que se ve", "tension": hypothesis, "idea": "Convertir la prueba o experiencia verificable en el protagonista de la comunicación.", "medios": ["punto de venta", "video corto", "radio/local"], "control_de_propiedad": "Solo funciona si la prueba pertenece realmente a la marca."}, {"nombre": "La elección se vuelve fácil", "tension": "La fricción de elegir puede ser más fuerte que la falta de notoriedad.", "idea": "Diseñar señales que reduzcan la duda en el momento y lugar de decisión.", "medios": ["exhibición", "digital de proximidad", "material comercial"], "control_de_propiedad": "No reemplazar una debilidad real de producto, precio o acceso."}, {"nombre": "Una historia con territorio", "tension": "La pertenencia puede ser relevante cuando se demuestra, no cuando se declama.", "idea": "Encontrar una verdad local comprobable que conecte marca, personas y ocasión.", "medios": ["acciones locales", "prensa regional", "redes"], "control_de_propiedad": "Evitar estereotipos territoriales y frases intercambiables."}], "recomendacion": "Elegir una ruta solo después de aplicar los controles de estrategia, marca y propiedad a una primera ejecución."}
    return {"tipo": "curaduría de aprendizaje", "aprendizajes_confirmados": learning, "propuesta": "Transformar resultados, aprobaciones y rechazos en reglas fechadas, con evidencia y alcance explícitos.", "siguiente_paso": "Validar los aprendizajes propuestos antes de reutilizarlos en otro proyecto."}


def run_agent(agent_key: str, project_name: str, brief: dict, strategy: dict, decision: dict, memory: dict, learning: list[dict], instruction: str) -> tuple[dict, str]:
    local = local_agent_output(agent_key, project_name, brief, strategy, decision, memory, learning, instruction)
    s = get_settings()
    if not s.openai_api_key:
        return local, "OLIVA OS — guía local"
    payload = {"agente": agent_key, "proyecto": project_name, "instruccion": instruction, "brief": brief, "estrategia": strategy, "decision": decision, "memoria_cliente": memory, "aprendizajes": learning, "salida_local_de_referencia": local}
    if agent_key == "creative_director":
        payload["lentes_de_referencia_oliva"] = creative_reference_context()
    try:
        text, model = responses_text({"model": model_for_agent(s, agent_key), "instructions": AGENT_PROMPT, "input": json.dumps(payload, ensure_ascii=False), "text": {"format": {"type": "json_object"}}})
        data = json.loads(text or "{}")
        return data or local, model
    except Exception:
        return local, "OLIVA OS — guía local"


def local_creative_concepts(project_name: str, brief: dict, strategy: dict, decision: dict, memory: dict, instruction: str) -> dict:
    route = decision.get("route_key", "ruta_1").replace("_", " ")
    basis = decision.get("rationale") or "la decisión estratégica aprobada"
    product = brief.get("product") or project_name
    territory = brief.get("territory") or "el territorio prioritario"
    tone = brief.get("brand_tone") or memory.get("tone") or "cercano, claro y sin exageración"
    proof = brief.get("proof") or "una prueba concreta que la marca pueda sostener"
    return {
        "base_aprobada": {"ruta": route, "fundamento": basis, "plan": decision.get("launch_plan", ""), "supuesto_visible": "Las propuestas son plataformas editables; requieren elección humana antes de producir piezas."},
        "desafio_creativo": f"Convertir {basis} en una plataforma propia para {product}, que pueda vivir en formatos de campaña sin reducirse a un eslogan.",
        "efecto_buscado": brief.get("behavior") or "Que el público prioritario considere y pruebe la propuesta en su ocasión real de elección.",
        "territorios": [
            {"id": "territorio_1", "nombre": "La ocasión cambia la categoría", "tension": brief.get("motivations") or "La categoría suele aparecer en ocasiones acotadas, aunque la necesidad puede ser cotidiana.", "idea_central": f"Reencuadrar {product} para que deje de pertenecer a una sola ocasión y gane un lugar concreto en el día a día.", "rol_de_marca": "La marca habilita esa nueva ocasión con una propuesta reconocible, no con una promesa genérica.", "tipo_de_campana": "Campaña de reposicionamiento y lanzamiento", "estilo": "Observación cotidiana, contrastes simples y una pregunta que abra la categoría.", "tono": tone, "medios": ["video corto", "radio/local", "punto de venta", "social"], "propiedad": f"Solo funciona si la marca demuestra {proof} y conecta esa prueba con la nueva ocasión.", "riesgos_y_cliches": "No usar nostalgia vacía ni una estética artesanal intercambiable.", "control": "Prometedora: desarrollar una primera ejecución y aplicar la prueba de sustitución de marca."},
            {"id": "territorio_2", "nombre": "La prueba entra en escena", "tension": "En una góndola o compra rápida, la diferencia debe poder entenderse antes de explicarse.", "idea_central": f"Hacer visible la prueba de {product}: convertir el origen, proceso o producto real en una señal de elección inmediata.", "rol_de_marca": "La marca transforma una credencial verificable en una experiencia de elección.", "tipo_de_campana": "Campaña de prueba y preferencia", "estilo": "Dirección de arte precisa, producto protagonista y demostración sin exceso de adjetivos.", "tono": tone, "medios": ["exhibición", "vía pública de proximidad", "video producto", "material comercial"], "propiedad": f"Depende de una prueba real: {proof}.", "riesgos_y_cliches": "No convertir la calidad en una frase genérica o en food porn sin estrategia.", "control": "Requiere validar que la prueba sea cierta, visible y relevante para el canal."},
            {"id": "territorio_3", "nombre": "Un ritual hecho acá", "tension": f"La pertenencia puede ser una verdad si se conecta con comportamientos reales de {territory}, no si se limita a nombrar lugares.", "idea_central": f"Encontrar un ritual cotidiano y local donde {product} se vuelva una elección inevitable, sin caricaturizar el territorio.", "rol_de_marca": "La marca participa de un hábito local con códigos propios y una razón concreta para estar ahí.", "tipo_de_campana": "Campaña territorial y de activación", "estilo": "Documental estilizado, voces reales y códigos locales contemporáneos.", "tono": tone, "medios": ["activación", "prensa regional", "radio", "creadores locales"], "propiedad": "La idea necesita una verdad cultural o de distribución demostrable del territorio.", "riesgos_y_cliches": "Evitar folklore decorativo, estereotipos o localismo de postal.", "control": "Exploratoria: elegir solo si se identifica una verdad local verificable."},
        ],
        "recomendacion": {"territorio_id": "territorio_1", "por_que": "Es el que mejor traduce la ruta aprobada en una plataforma de campaña amplia y luego permite construir demostraciones y activaciones."},
        "sistema_creativo": {"idea_rectora": "Se define al elegir y editar una plataforma.", "codigos_verbales": tone, "universo_visual": "Se construye desde el concepto elegido, producto real y códigos de marca disponibles.", "universo_sonoro": "Definir voces, ritmo y elementos de recordación después de elegir el territorio.", "fijos": ["Ruta estratégica aprobada", "prueba real de producto o marca", "restricciones del brief"], "variables": ["Medio", "territorio", "segmento", "momento de compra"], "prohibidos": ["Clichés de categoría", "promesas no demostrables", "estética sin idea"], "nota_del_director": instruction or "Editá cualquiera de las plataformas antes de elegirla; la selección habilita la carga y revisión de materiales."},
    }


def generate_creative_concepts(project_name: str, brief: dict, strategy: dict, decision: dict, memory: dict, instruction: str) -> tuple[dict, str]:
    local = local_creative_concepts(project_name, brief, strategy, decision, memory, instruction)
    s = get_settings()
    if not s.openai_api_key:
        return local, "OLIVA Creative Director — guía local"
    payload = {"proyecto": project_name, "brief": brief, "estrategia": strategy, "decision_aprobada": decision, "memoria_cliente": memory, "foco_adicional": instruction, "lentes_de_referencia_oliva": creative_reference_context(), "estructura_de_referencia": local}
    try:
        text, model = responses_text({"model": s.openai_creative_model, "instructions": CREATIVE_DIRECTION_PROMPT, "input": json.dumps(payload, ensure_ascii=False), "text": {"format": {"type": "json_object"}}})
        data = json.loads(text or "{}")
        return data if isinstance(data.get("territorios"), list) and len(data["territorios"]) == 3 else local, model
    except Exception:
        return local, "OLIVA Creative Director — guía local (API no disponible)"


def creative_table(project_name: str, brief: dict, decision: dict, board: dict, plan: dict, question: str) -> tuple[dict, str]:
    base = board.get("base_aprobada", {}) if isinstance(board, dict) else {}
    local = {
        "pregunta": question,
        "intervenciones": [
            {"rol": "Estrategia", "acuerdo": f"La conversación debe conservar la ruta {decision.get('route_key', 'aprobada')}.", "objecion": "No usar una ocurrencia creativa para prometer algo que el brief no sostiene.", "aporte_concreto": "Definir qué comportamiento cambia esta propuesta y qué señal lo comprobaría.", "prueba_de_propiedad": "¿La propuesta depende de una verdad específica de la marca?"},
            {"rol": "Dirección Creativa", "acuerdo": f"La idea rectora es {base.get('idea_central', 'la plataforma elegida')}.", "objecion": "Descartar cualquier frase o escena que pueda cambiar de marca sin perder sentido.", "aporte_concreto": "Traducir la pregunta del equipo en una escena, giro y remate memorables.", "prueba_de_propiedad": "¿Hay una sola frase y gesto que el público pueda repetir?"},
            {"rol": "Dirección de Arte", "acuerdo": "El sistema visual debe hacer reconocible la idea antes de explicar el producto.", "objecion": "No usar estética de categoría como reemplazo de concepto.", "aporte_concreto": "Elegir una imagen madre, una regla de encuadre y un código visual persistente.", "prueba_de_propiedad": "¿El mundo visual sigue siendo de la marca sin el logo?"},
            {"rol": "Producción", "acuerdo": "La ejecución debe ser viable y adaptable desde el inicio.", "objecion": "No confundir ambición con una lista de requerimientos sin función.", "aporte_concreto": "Convertir la idea en una primera pieza piloto con responsable, formato y aprendizaje esperado.", "prueba_de_propiedad": "¿La producción preserva el giro central en cada formato?"},
        ],
        "cierre": {"mantener": "La decisión estratégica y la plataforma elegida.", "cambiar": "Solo la ejecución que el equipo considere insuficiente.", "probar": "Una pieza piloto antes de extender la idea a todos los soportes.", "no_hacer": "Recalcular la estrategia por un comentario o una edición creativa."},
    }
    s = get_settings()
    if not s.openai_api_key:
        return local, "Mesa OLIVA — guía local"
    payload = {"proyecto": project_name, "brief": brief, "decision": decision, "plataforma": board, "plan": plan, "pregunta_del_equipo": question, "lentes_oliva": creative_reference_context(), "referencia_local": local}
    try:
        text, model = responses_text({"model": s.openai_creative_model, "instructions": CREATIVE_TABLE_PROMPT, "input": json.dumps(payload, ensure_ascii=False), "text": {"format": {"type": "json_object"}}})
        data = json.loads(text or "{}")
        return data if isinstance(data.get("intervenciones"), list) and len(data["intervenciones"]) >= 3 else local, model
    except Exception:
        return local, "Mesa OLIVA — guía local (API no disponible)"


def local_campaign_plan(project_name: str, brief: dict, decision: dict, board: dict, territory_id: str) -> dict:
    """Create an editable production and media plan without claiming unaudited audience data."""
    territories = board.get("territorios", []) if isinstance(board, dict) else []
    territory = next((item for item in territories if item.get("id") == territory_id), territories[0] if territories else {})
    zone = brief.get("territory") or "la zona prioritaria definida en el proyecto"
    campaign = territory.get("nombre", "la plataforma elegida")
    idea = territory.get("idea_central", "la idea central aprobada")
    selected_media = territory.get("medios", []) or ["punto de venta", "radio local", "social"]
    product = brief.get("product") or project_name
    return {
        "base_aprobada": {
            "plataforma": campaign,
            "territorio": zone,
            "idea_central": idea,
            "ruta": decision.get("route_key", "ruta aprobada").replace("_", " "),
        },
        "criterio_de_medios": {
            "estado": "Propuesta de trabajo; no sustituye una medición certificada de consumo de medios.",
            "lectura_local": f"Para {zone}, se combinan contacto cercano al momento de compra, alcance regional y frecuencia en formatos cotidianos. Ajustar con datos de plaza, disponibilidad y costos reales.",
            "evidencia_a_sumar": "Agregar estudios de medios, datos de distribuidores, inversión histórica o entrevistas de plaza cuando estén disponibles. Hasta entonces, cada soporte es una hipótesis explícita.",
        },
        "piezas_creativas": [
            {"id": "pieza_1", "nombre": "Pieza madre de lanzamiento", "formato": "Video vertical 15–20 s", "funcion": f"Presentar {idea} con {product} como prueba y cierre de marca.", "prioridad": "Alta", "momento": "Lanzamiento / social y pantallas de punto de venta"},
            {"id": "pieza_2", "nombre": "Mensaje de radio local", "formato": "Cuña 20–30 s", "funcion": "Construir frecuencia y recordación oral con una situación cotidiana y llamado al punto de venta.", "prioridad": "Alta", "momento": "Franja de movilidad, recreo o merienda según la plaza"},
            {"id": "pieza_3", "nombre": "Exhibición de elección", "formato": "Cartel de góndola / mostrador", "funcion": "Resolver la elección rápida: producto, prueba, precio o llamada a probar, con lectura inmediata.", "prioridad": "Alta", "momento": "Punto de venta"},
            {"id": "pieza_4", "nombre": "Contenido de cercanía", "formato": "Historias y piezas estáticas", "funcion": "Traducir la plataforma a momentos, preguntas y pruebas que admitan variación por barrio o localidad.", "prioridad": "Media", "momento": "Social / creadores y comercios locales"},
        ],
        "soportes_de_medios": [
            {"id": "soporte_1", "soporte": "Punto de venta y canal comercial", "rol": "Capturar la decisión donde el producto se elige; priorizar comercios y zonas con disponibilidad real.", "cobertura": zone, "prioridad": "Alta", "indicador": "Exhibiciones activas, reposición y rotación por punto"},
            {"id": "soporte_2", "soporte": "Radio y audio local", "rol": "Aportar frecuencia y cercanía en rutinas de movilidad y consumo cotidiano.", "cobertura": "Emisoras y audio con alcance comprobable en " + zone, "prioridad": "Alta", "indicador": "Cobertura contratada, frecuencia y consultas/ventas por plaza"},
            {"id": "soporte_3", "soporte": "Social geolocalizado", "rol": "Alcanzar públicos próximos al área de distribución y llevarlos a una acción o punto concreto.", "cobertura": "Radio de distribución real, no territorio nacional por defecto", "prioridad": "Media", "indicador": "Alcance local, visualizaciones completas, visitas o mensajes"},
            {"id": "soporte_4", "soporte": "Prensa y cuentas de cercanía", "rol": "Dar contexto, credibilidad o activación en plazas donde esos medios tengan lectura efectiva.", "cobertura": zone, "prioridad": "A validar", "indicador": "Audiencia declarada, respuestas y tráfico al comercio"},
        ],
        "fases": [
            {"fase": "1. Preparar", "objetivo": "Asegurar disponibilidad, exhibición y una pieza madre antes de ampliar alcance.", "acciones": "Elegir comercios/puntos piloto, adaptar materiales y confirmar costos y cobertura."},
            {"fase": "2. Lanzar y aprender", "objetivo": "Comprobar si la plataforma genera elección en la zona prioritaria.", "acciones": "Activar punto de venta, radio/audio y social local; registrar rotación, reposición y conversación."},
            {"fase": "3. Ajustar y escalar", "objetivo": "Conservar lo que funciona y corregir lo que no antes de ampliar plazas.", "acciones": "Comparar plazas, soportes y mensajes; aprobar variantes y solo entonces aumentar inversión."},
        ],
        "medios_sugeridos_por_plataforma": selected_media,
        "control_final": "Cada pieza debe explicar qué conducta busca, cómo desarrolla la idea central y por qué ese soporte cumple un rol que otro no puede reemplazar.",
    }


def generate_campaign_plan(project_name: str, brief: dict, decision: dict, board: dict, territory_id: str) -> tuple[dict, str]:
    local = local_campaign_plan(project_name, brief, decision, board, territory_id)
    s = get_settings()
    if not s.openai_api_key:
        return local, "OLIVA Campaign Planner — guía local"
    payload = {"proyecto": project_name, "brief": brief, "decision_aprobada": decision, "plataforma_creativa": board, "territorio_elegido": territory_id, "estructura_de_referencia": local}
    instructions = "Sos OLIVA Campaign Planner. Construí un plan editable de piezas, soportes y fases desde una plataforma creativa aprobada. Localizá para el territorio definido, pero no inventes datos de consumo de medios: marcá como hipótesis todo soporte no respaldado por una fuente. Cada medio debe tener un rol específico, indicador y cobertura realista. Devolvé JSON con piezas_creativas, soportes_de_medios, fases, criterio_de_medios y control_final."
    try:
        text, model = responses_text({"model": s.openai_operations_model, "instructions": instructions, "input": json.dumps(payload, ensure_ascii=False), "text": {"format": {"type": "json_object"}}})
        data = json.loads(text or "{}")
        return data if isinstance(data.get("piezas_creativas"), list) and isinstance(data.get("soportes_de_medios"), list) else local, model
    except Exception:
        return local, "OLIVA Campaign Planner — guía local (API no disponible)"


def local_production_proposals(project_name: str, brief: dict, board: dict, plan: dict) -> dict:
    """Turn an approved plan into a concise creative proposal, never a pasted brief."""
    selected_id = board.get("selected_territory_id", "") if isinstance(board, dict) else ""
    territories = board.get("territorios", []) if isinstance(board, dict) else []
    territory = next((item for item in territories if item.get("id") == selected_id), territories[0] if territories else {})
    base = plan.get("base_aprobada", {}) if isinstance(plan, dict) else {}
    product = (brief.get("product") or project_name).split(".")[0].strip()[:110]
    audience = (brief.get("audience") or "el público prioritario").split(".")[0].strip()[:180]
    zone = base.get("territorio") or brief.get("territory") or "la plaza definida"
    tone = territory.get("tono") or brief.get("brand_tone") or "cercano, preciso y con una observación cotidiana"
    proof = (brief.get("proof") or "el producto real y su elaboración").split(".")[0].strip()[:160]
    is_alfajor_case = "alfajor" in product.lower() or "alfajor" in project_name.lower()
    if is_alfajor_case:
        campaign = "No esperes el viaje"
        core = "El alfajor artesanal no tiene que esperar la ruta, la terminal ni el regalo: también puede convertir un corte cualquiera en un pequeño viaje."
        verbal = "No esperes el viaje. Flor de Panzada."
        scripts = [
            {"id":"guion_video_15","pieza":"Película madre · No esperes el viaje","medio":"Social, pantallas y video corto","duracion_formato":"20 s · vertical 9:16","objetivo":"Mover al alfajor artesanal del recuerdo de viaje a la pausa elegida de todos los días.","propuesta":"Abrimos en una terminal: una voz anuncia una salida. Corte revelador: no es una terminal, es el timbre del recreo. La épica del viaje se traslada a una escena mínima y reconocible.","guion":"0–3 s · SFX terminal. VO: «Atención pasajeros…».\n3–6 s · Timbre de recreo. Corte a chicos saliendo y un adulto abriendo la mochila.\n6–12 s · Primer plano honesto del alfajor, sin food porn. Un chico: «¿Pero no eran para viajar?»\n12–17 s · Respuesta: «¿Y quién dijo que hoy no?»\n17–20 s · Pack real + «No esperes el viaje. Flor de Panzada.»","produccion":"Una locación escolar/comercial real, casting con adultos responsables, producto y packaging definitivos. Mantener el giro en montaje, no en explicación.","control":"¿El remate transforma de verdad el rol de la categoría o podría decirlo cualquier snack?"},
            {"id":"guion_radio_30","pieza":"Radio · Próxima parada","medio":"Radio local y audio digital","duracion_formato":"30 s · audio","objetivo":"Construir una idea sonora propia que la gente pueda repetir.","propuesta":"Usar el código inconfundible de la terminal para anunciar destinos domésticos: recreo, salida del trabajo, merienda. La marca no narra; irrumpe con el giro.","guion":"SFX: parlante de terminal, rueda de valija.\nLOCUTOR: «Atención pasajeros. Próxima parada: recreo. Andén dos: la salida del trabajo. Servicio especial: esa merienda que te salva el día.»\nSFX: timbre escolar.\nVO JOVEN: «¿Un alfajor de viaje?»\nVO ADULTO: «No. Un alfajor para no esperar el viaje.»\nLOCUTOR: «Flor de Panzada. No esperes el viaje.»","produccion":"Diseñar una identidad sonora propia: parlante, timbre, pausa y cierre. Validar disponibilidad y mención de puntos de venta antes de agregarla.","control":"¿La idea se entiende sin imagen y la frase final queda en la cabeza sin explicar el chiste?"},
            {"id":"guion_pdv","pieza":"Punto de venta · Próxima parada","medio":"Exhibidor, stopper y mostrador","duracion_formato":"Una lectura de 2 segundos","objetivo":"Hacer que la idea aparezca exactamente donde se decide la compra.","propuesta":"El exhibidor toma la lógica de un panel de partidas, pero en vez de ciudades anuncia momentos: RECREO / MERIENDA / VOLVER A CASA. El producto ocupa el lugar de la salida.","guion":"Titular: «PRÓXIMA PARADA: UN BUEN MOMENTO».\nSubtítulo mínimo: «No esperes el viaje».\nProducto/pack real al centro.\nCierre: Flor de Panzada.\nNo sumar precio, origen ni promesas si no están confirmadas.","produccion":"Adaptar a medidas reales del comercio. Probar legibilidad desde un metro y resolver reposición sin tapar el pack.","control":"¿Se entiende sin leer un párrafo y hace que el producto parezca una elección de ahora?"},
            {"id":"guion_social_local","pieza":"Social · Destinos de todos los días","medio":"Reels, historias y cuentas de cercanía","duracion_formato":"4 piezas de 6–10 s","objetivo":"Extender una idea madre sin convertirla en posteos de producto.","propuesta":"Cada pieza abre como un anuncio de viaje y revela un destino cotidiano: el recreo, el banco de la plaza, la salida del club, el viaje en ómnibus de todos los días.","guion":"Formato fijo: 0–2 s, placa/sonido de terminal. 2–6 s, giro hacia un destino cotidiano. 6–9 s, alfajor y frase: «No esperes el viaje».\nVariantes: «Próxima parada: recreo» / «Próxima parada: después del club» / «Próxima parada: cinco minutos para vos».\nNo usar locaciones ni testimonios falsos.","produccion":"Armar una matriz de destinos que existan en cada plaza. Subtítulos siempre; una versión limpia para pauta y otra con información comercial verificable.","control":"¿Todas las piezas podrían reconocerse sin logo como parte del mismo sistema?"},
        ]
    else:
        campaign = territory.get("nombre", "La idea que entra en la vida real")
        core = (territory.get("idea_central") or "Hacer que la propuesta deje de ser una descripción y se vuelva una elección concreta.").split(".")[0][:240]
        verbal = "Una idea propia, una escena y una acción concreta."
        scripts = [
            {"id":"guion_video_15","pieza":"Película madre","medio":"Video y social","duracion_formato":"15–20 s","objetivo":"Presentar el conflicto y resolverlo con un giro propio de la marca.","propuesta":"Una sola escena que haga visible la tensión; el producto o servicio entra como resolución, no como aparición decorativa.","guion":"0–3 s · Situación reconocible.\n3–8 s · Conflicto o contradicción.\n8–14 s · Giro: la marca vuelve inevitable la resolución.\n14–20 s · Producto real, frase de campaña y acción.","produccion":"Definir producto, locación, activo de marca y una versión silenciosa antes de filmar.","control":"¿Hay una idea que sobreviva sin música, estética ni logo?"},
            {"id":"guion_radio_30","pieza":"Audio con giro","medio":"Radio y audio digital","duracion_formato":"30 s","objetivo":"Hacer que la tensión se escuche antes de que la marca sea nombrada.","propuesta":"Construir una escena sonora donde el giro de la plataforma sea la razón de recordar la marca.","guion":"0–8 s · Universo sonoro.\n8–18 s · Conflicto en diálogo.\n18–25 s · Giro de marca.\n25–30 s · Frase de campaña, marca y acción confirmada.","produccion":"Definir voz, ritmo y sonido propio; no agregar menciones que el canal no pueda sostener.","control":"¿Se recuerda por su situación y no por una locución de oferta?"},
            {"id":"guion_pdv","pieza":"Decisión en 2 segundos","medio":"Punto de venta","duracion_formato":"Exhibición y cartel","objetivo":"Concentrar la idea en una lectura inmediata.","propuesta":"Una pregunta o frase, producto/prueba y acción. Nada más.","guion":"1. Tensión en cinco palabras.\n2. Producto real / prueba comprobable.\n3. Marca y acción de compra.","produccion":"Confirmar medidas, stock y condición comercial antes de diseñar.","control":"¿Se puede leer de pasada y sigue siendo la misma idea?"},
        ]
    return {
        "creative_version": 2,
        "propuesta_de_campana": {"nombre": campaign, "idea_rectora": core, "publico": audience, "territorio": zone, "promesa_de_trabajo": core, "tono_y_sistema": f"{tone}. Frase rectora: «{verbal}»"},
        "criterio_creativo": {
            "principios": [
                "Una observación reconocible antes que una descripción del producto.",
                "Un giro que haga propia a la marca, no una variante estética de la categoría.",
                "Una idea madre capaz de cambiar de medio sin perder reconocimiento.",
                "Arte, audio y craft al servicio de la idea y de la conducta buscada.",
            ],
            "referencias": creative_reference_context(),
            "aclaracion": "Estas referencias orientan el criterio de OLIVA; no se imita ni se atribuye una idea a ninguna persona.",
        },
        "propuestas_de_produccion": scripts,
        "mesa_de_agentes": [
            {"agente": "OLIVA Strategy", "rol": "Guardián del problema", "aporte": f"Fija el desafío y evita que la campaña reemplace una decisión de negocio: {core}", "control": "La ejecución debe conducir a la conducta definida, no sólo a notoriedad."},
            {"agente": "Director Creativo", "rol": "Idea y propiedad", "aporte": f"Convierte la tensión en una campaña con una regla única: {core}", "control": "Si se puede cambiar el logo sin que se rompa, se vuelve a trabajar."},
            {"agente": "Redactor", "rol": "Arquitectura verbal", "aporte": "Construye pregunta, demostración y cierre; no fabrica slogans aislados.", "control": "Cada palabra debe hacer visible la ocasión, la prueba o la acción."},
            {"agente": "Director de Arte", "rol": "Sistema visual", "aporte": "Define cómo la idea vive en imagen, producto, encuadre, color y composición antes de producir variantes.", "control": "La estética debe demostrar la idea y no disimular su ausencia."},
            {"agente": "Planificador de Medios", "rol": "Rol de soportes", "aporte": f"Localiza contacto, cobertura e indicadores para {zone} sin confundir hipótesis con medición.", "control": "Cada soporte debe justificar qué hace mejor que los demás."},
            {"agente": "Guardián de Marca y Producción", "rol": "Viabilidad", "aporte": "Controla tono, activos reales, disponibilidad, restricciones y consistencia entre piezas.", "control": "No aprobar una promesa, precio, punto de venta o activo visual que no esté confirmado."},
        ],
        "bocetos_visuales": [
            {"id": "boceto_tablero", "titulo": "Tablero de dirección de arte", "pieza": "Sistema de campaña", "estado": "Boceto para validar, no arte final", "asset_url": "/creative/alfajores-concept-board-v1.png" if is_alfajor_case else "", "direccion": f"Cuatro momentos coherentes: ocasión cotidiana, prueba de {product}, elección en punto de venta y formato social. El lenguaje visual debe sostener {core}.", "prompt_de_produccion": f"Tablero de cuatro fotogramas publicitarios para {product}, territorio {zone}; ocasión cotidiana real, prueba visual verificable, exhibición de compra y formato social; tono {tone}; sin texto inventado, sin logos falsos, sin clichés de categoría."},
            {"id": "boceto_pdv", "titulo": "Boceto de elección en punto de venta", "pieza": "Exhibidor y cartel", "estado": "Dirección de arte a visualizar", "asset_url": "", "direccion": "Jerarquía en tres golpes de vista: ocasión/pregunta, producto con prueba y acción. El producto real debe dominar la composición.", "prompt_de_produccion": f"Mockup de exhibición comercial para {product}; lectura inmediata, espacio para pack real y prueba real, sistema visual coherente con {core}, sin tipografía inventada ni precios falsos."},
        ],
        "faltantes_de_produccion": ["Producto, packaging y logos finales", "Lista de puntos de venta y cobertura confirmada", "Restricciones legales/promocionales", "Presupuesto, responsables y calendario de producción", "Activos visuales y sonoros aprobados de la marca"],
        "nota_del_director": "Son guiones de trabajo editables, no piezas finales. Ajustalos antes de producir y cargá luego los bocetos o materiales resultantes para revisión.",
    }


def generate_production_proposals(project_name: str, brief: dict, board: dict, plan: dict) -> tuple[dict, str]:
    local = local_production_proposals(project_name, brief, board, plan)
    s = get_settings()
    if not s.openai_api_key:
        return local, "OLIVA Creative Director — producción guiada local"
    payload = {"proyecto": project_name, "brief": brief, "plataforma": board, "plan_de_campana": plan, "estructura_de_referencia": local}
    instructions = "Sos OLIVA Creative Director en fase de producción. No pegues el brief ni describas una ejecución genérica: encontrá una idea central breve, una tensión, un giro y una frase rectora. Cada guion debe tener escenas concretas, audio/imagen cuando corresponda, remate y un motivo por el que sólo esta marca puede hacerlo. No imites a publicistas vivos; aplicá los lentes de criterio provistos. Antes de escribir, rechazá cualquier idea intercambiable, explicación larga o estética sin concepto. Desde una plataforma y plan aprobados, proponé guiones de trabajo editables para video, radio/audio, punto de venta y social. Cada propuesta debe incluir objetivo, público, medio/formato, vínculo con la idea, guion técnico, requisitos y control final. No inventes logos, precios, resultados, disponibilidad ni datos de consumo. Localizá sólo con datos presentes y marcá faltantes. Devolvé JSON con propuesta_de_campana, propuestas_de_produccion, faltantes_de_produccion y nota_del_director.\nLENTES CREATIVOS OLIVA:\n" + creative_reference_context()
    try:
        text, model = responses_text({"model": s.openai_creative_model, "instructions": instructions, "input": json.dumps(payload, ensure_ascii=False), "text": {"format": {"type": "json_object"}}})
        data = json.loads(text or "{}")
        if isinstance(data.get("propuestas_de_produccion"), list):
            # El modelo puede enriquecer la propuesta, pero la interfaz necesita
            # siempre la mesa, los bocetos y el criterio que hacen visible el trabajo.
            for key, value in local.items():
                data.setdefault(key, value)
            data["creative_version"] = 2
            return data, model
        return local, model
    except Exception:
        return local, "OLIVA Creative Director — producción guiada local (API no disponible)"
CREATIVE_PROMPT="""Sos el comité creativo de OLIVA. Evaluá contra la estrategia aprobada y contexto de marca. No premies estética sin estrategia. Aplicá sustitución de logo, cambio de categoría y eliminación de estética. Puntúa 0-5 estrategia, verdad_humana, rol_de_marca, apropiabilidad, originalidad, claridad, fertilidad, coherencia, adecuacion_al_medio, viabilidad. Las primeras críticas son estrategia, coherencia y apropiabilidad. Respondé SOLO JSON: verdict (aprobable/revisar/no_alineada), scores y evaluation concreta."""
def evaluate_creative(path:Path,content_type:str,name:str,medium:str,rationale:str,strategy:dict,brand_context:str)->dict:
    s=get_settings()
    def local_review(reason: str = "") -> dict:
        decision=(strategy.get("decision_estrategica") or {}) if isinstance(strategy,dict) else {}
        route=decision.get("ruta") or decision.get("route_key", "ruta de trabajo")
        has_rationale=len(rationale.strip()) >= 40
        scores={key:0 for key in SCORE_KEYS}
        scores["estrategia"]=2 if has_rationale else 1
        scores["claridad"]=2 if medium.strip() else 1
        scores["viabilidad"]=2 if medium.strip() else 1
        unavailable = f" {reason}" if reason else ""
        return {"verdict":"revisar","scores":scores,"evaluation":f"Control editorial local: la pieza debe demostrar cómo responde a {str(route).replace('_', ' ')}. {'El fundamento aporta una base inicial; revisá que explique audiencia, promesa y conducta a cambiar.' if has_rationale else 'Falta un fundamento de al menos una idea completa: audiencia, promesa, conducta esperada y rol del medio.'} La evaluación visual y de originalidad se completa al configurar la IA.{unavailable}","model_used":"OLIVA Creative Review — guía local"}
    if not s.openai_api_key:
        return local_review()
    raw=path.read_bytes();content=[{"type":"input_text","text":json.dumps({"nombre":name,"medio":medium,"fundamento":rationale,"estrategia":strategy,"marca":brand_context},ensure_ascii=False)}]
    if content_type.startswith("image/"):content.append({"type":"input_image","image_url":f"data:{content_type};base64,{base64.b64encode(raw).decode()}","detail":"high"})
    else:content.append({"type":"input_text","text":extract_text(raw,content_type)[:60000]})
    try:
        text,model=responses_text({"model":s.openai_vision_model,"instructions":CREATIVE_PROMPT,"input":[{"role":"user","content":content}],"text":{"format":{"type":"json_object"}}});data=json.loads(text or "{}");data["model_used"]=model;data["scores"]={k:int(data.get("scores",{}).get(k,0)) for k in SCORE_KEYS};return data
    except Exception:
        return local_review("La revisión asistida quedó pendiente por una respuesta temporalmente no disponible de la IA.")
