import base64,json
from pathlib import Path
from .config import get_settings
from .documents import extract_text
from .strategy import response_text,responses_payload,responses_text
FESTIVAL_DOMAINS=["canneslions.com","dandad.org","oneclub.org","clios.com","effie.org","fiapawards.com","elojodeiberoamerica.com","elsolfestival.com","sxsw.com","desachate.com","circulopublicidad.com"]
MARKET_RESEARCH_DOMAINS=[
    "kantar.com", "nielseniq.com", "ipsos.com", "gk.com", "euromonitor.com",
    "lanacion.com.ar", "clarin.com", "cronista.com", "ambito.com", "infobae.com",
    "apertura.com", "mercado.com.ar", "iprofesional.com", "adlatina.com",
    "marketingdirecto.com", "reddit.com",
]
SCORE_KEYS=["estrategia","verdad_humana","rol_de_marca","apropiabilidad","originalidad","claridad","fertilidad","coherencia","adecuacion_al_medio","viabilidad"]

AGENT_PROMPT="""Sos un agente especializado de OLIVA Intelligence. Trabajá con trazabilidad: separá hechos, inferencias, hipótesis y faltantes. No inventes resultados, antecedentes ni fuentes. La salida debe ser JSON válido, accionable y apto para aprobación humana."""
CREATIVE_DIRECTION_PROMPT="""Sos OLIVA Creative Director. Trabajá exclusivamente sobre la estrategia y ruta aprobadas. Antes de proponer, controlá estrategia, marca y propiedad: si la idea serviría igual para cualquier marca, marcala débil y reformulala. Devolvé JSON con desafio_creativo, efecto_buscado, base_aprobada, territorios (exactamente 3), recomendacion y sistema_creativo. Cada territorio debe incluir id, nombre, tension, idea_central, rol_de_marca, tipo_de_campana, estilo, tono, medios, propiedad, riesgos_y_cliches y control. No escribas piezas finales ni inventes evidencia."""
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

def project_web_research(project_name:str, objective:str, query:str)->tuple[str,list[dict[str,str]],str]:
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
    try:
        body=responses_payload({
            "model":s.openai_search_model,
            "reasoning":{"effort":"low"},
            "tools":[{"type":"web_search","search_context_size":"high","filters":{"allowed_domains":MARKET_RESEARCH_DOMAINS}}],
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
    try:
        text, model = responses_text({"model": s.openai_model, "instructions": AGENT_PROMPT, "input": json.dumps(payload, ensure_ascii=False), "text": {"format": {"type": "json_object"}}})
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
    payload = {"proyecto": project_name, "brief": brief, "estrategia": strategy, "decision_aprobada": decision, "memoria_cliente": memory, "foco_adicional": instruction, "estructura_de_referencia": local}
    try:
        text, model = responses_text({"model": s.openai_model, "instructions": CREATIVE_DIRECTION_PROMPT, "input": json.dumps(payload, ensure_ascii=False), "text": {"format": {"type": "json_object"}}})
        data = json.loads(text or "{}")
        return data if isinstance(data.get("territorios"), list) and len(data["territorios"]) == 3 else local, model
    except Exception:
        return local, "OLIVA Creative Director — guía local (API no disponible)"
CREATIVE_PROMPT="""Sos el comité creativo de OLIVA. Evaluá contra la estrategia aprobada y contexto de marca. No premies estética sin estrategia. Aplicá sustitución de logo, cambio de categoría y eliminación de estética. Puntúa 0-5 estrategia, verdad_humana, rol_de_marca, apropiabilidad, originalidad, claridad, fertilidad, coherencia, adecuacion_al_medio, viabilidad. Las primeras críticas son estrategia, coherencia y apropiabilidad. Respondé SOLO JSON: verdict (aprobable/revisar/no_alineada), scores y evaluation concreta."""
def evaluate_creative(path:Path,content_type:str,name:str,medium:str,rationale:str,strategy:dict,brand_context:str)->dict:
    s=get_settings()
    if not s.openai_api_key:
        decision=(strategy.get("decision_estrategica") or {}) if isinstance(strategy,dict) else {}
        route=decision.get("ruta") or decision.get("route_key", "ruta de trabajo")
        has_rationale=len(rationale.strip()) >= 40
        scores={key:0 for key in SCORE_KEYS}
        scores["estrategia"]=2 if has_rationale else 1
        scores["claridad"]=2 if medium.strip() else 1
        scores["viabilidad"]=2 if medium.strip() else 1
        return {"verdict":"revisar","scores":scores,"evaluation":f"Control editorial local: la pieza debe demostrar cómo responde a {str(route).replace('_', ' ')}. {'El fundamento aporta una base inicial; revisá que explique audiencia, promesa y conducta a cambiar.' if has_rationale else 'Falta un fundamento de al menos una idea completa: audiencia, promesa, conducta esperada y rol del medio.'} La evaluación visual y de originalidad se completa al configurar la IA.","model_used":"OLIVA Creative Review — guía local"}
    raw=path.read_bytes();content=[{"type":"input_text","text":json.dumps({"nombre":name,"medio":medium,"fundamento":rationale,"estrategia":strategy,"marca":brand_context},ensure_ascii=False)}]
    if content_type.startswith("image/"):content.append({"type":"input_image","image_url":f"data:{content_type};base64,{base64.b64encode(raw).decode()}","detail":"high"})
    else:content.append({"type":"input_text","text":extract_text(raw,content_type)[:60000]})
    text,model=responses_text({"model":s.openai_vision_model,"instructions":CREATIVE_PROMPT,"input":[{"role":"user","content":content}],"text":{"format":{"type":"json_object"}}});data=json.loads(text or "{}");data["model_used"]=model;data["scores"]={k:int(data.get("scores",{}).get(k,0)) for k in SCORE_KEYS};return data
