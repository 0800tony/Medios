import json, httpx
from openai import OpenAI
from .config import get_settings
from .models import Project

SYSTEM_PROMPT="""Sos OLIVA Strategy, Director de Planeamiento Estratégico Senior. Comprendé el problema antes de proponer comunicación. Separá hechos, evidencia, percepciones e hipótesis; buscá contradicciones; no confundas síntomas con causas. Si falta evidencia, decilo. Respondé exclusivamente JSON con diagnosis, evidence, hypotheses, contradictions, strategic_question y confidence."""
DOSSIER_KEYS=["resumen_ejecutivo","pedido_original","interpretacion_del_pedido","fuentes_y_calidad","que_sabemos","que_creemos","que_no_sabemos","diagnostico_del_problema","objetivos_diferenciados","comportamiento_a_cambiar","categoria_y_competencia","antecedentes_oliva","audiencias","barreras","tension_humana","insight","oportunidad_estrategica","rol_de_marca","promesa","razones_para_creer","tono","canales_y_contextos","ruta_1","ruta_2","ruta_3","comparacion_de_rutas","riesgos","indicadores","preguntas_indispensables","preguntas_importantes","preguntas_deseables","proxima_decision"]
MASTER_PROMPT="""Sos OLIVA Strategy, sistema de inteligencia estratégica de OLIVA Publicidad. Actuás como Director Senior de Planeamiento, no como redactor ni generador automático de campañas. No aceptes el problema declarado como verdadero. Nunca inventes datos. Separá hechos/evidencia, percepciones, hipótesis y vacíos. Diferenciá objetivos de negocio, comerciales, comunicación y medios. Analizá primero personas, luego organización y finalmente comunicación. Buscá contradicciones e intentá refutar hipótesis. Considerá Uruguay, Argentina e Interior, competencia, distribución e historia interna. Entregá exactamente tres rutas estratégicas genuinamente distintas y recomendá una ruta de trabajo, incluso si debe quedar bajo revisión. Todo queda pendiente de aprobación humana. Para lanzamientos y pymes del Interior, no exijas investigación externa formal como condición: distinguí validación ideal de aproximación suficiente para decidir. Aceptá como aproximación entrevistas breves a distribuidores/comercios, auditoría de góndola y precios, comparación con competidores, datos de ventas propios, capacidad productiva, observación, publicaciones sectoriales y estudios de terceros; marcá su nivel de confianza sin convertir aproximaciones en hechos universales. Si el brief ya contiene una aproximación para un tema, no la repitas como vacío crítico: registrala en fuentes_y_calidad como aproximación cargada y proponé aprender de ella durante el piloto. Respondé SOLO JSON válido sin markdown con exactamente estas claves: resumen_ejecutivo, pedido_original, interpretacion_del_pedido, fuentes_y_calidad, que_sabemos, que_creemos, que_no_sabemos, diagnostico_del_problema, objetivos_diferenciados, comportamiento_a_cambiar, categoria_y_competencia, antecedentes_oliva, audiencias, barreras, tension_humana, insight, oportunidad_estrategica, rol_de_marca, promesa, razones_para_creer, tono, canales_y_contextos, ruta_1, ruta_2, ruta_3, comparacion_de_rutas, riesgos, indicadores, preguntas_indispensables, preguntas_importantes, preguntas_deseables, proxima_decision. Cada elemento de que_no_sabemos debe identificar: vacio, por_que_importa, pregunta, aproximacion_suficiente y evidencia_ideal. proxima_decision debe incluir recomendacion_estrategica, por_que_ahora, primer_movimiento y no_hacer_aun; nunca uses solamente la frase genérica 'completar vacíos críticos'. Si falta base, decilo explícitamente y formulá la pregunta necesaria."""

def responses_payload(payload:dict)->dict:
    s=get_settings(); r=httpx.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {s.openai_api_key}","Content-Type":"application/json"},json=payload,timeout=180);r.raise_for_status();return r.json()
def response_text(body:dict)->str:
    if body.get("output_text"): return body["output_text"]
    return "\n".join(c.get("text","") for o in body.get("output",[]) for c in o.get("content",[]) if c.get("type")=="output_text")
def responses_text(payload:dict)->tuple[str,str]:
    b=responses_payload(payload);return response_text(b),b.get("model",payload.get("model","OpenAI"))
def local_dossier(project:Project,brief:dict[str,str],source_names:list[str])->dict[str,object]:
    insufficient="No cuento con información suficiente para sostener esta conclusión."
    request=(brief.get("request") or project.brief or "").lower()
    commercial=" ".join([brief.get("business_goal", ""), brief.get("commercial_goal", ""), brief.get("distribution", "")]).lower()
    gaps=[]; approximations=[]
    def add_gap(vacio:str,por_que_importa:str,pregunta:str,aproximacion:str,evidencia_ideal:str,brief_key:str):
        answer=brief.get(brief_key, "").strip()
        item={"vacio":vacio,"estado":"Aproximación pendiente","respuesta_cargada":"","por_que_importa":por_que_importa,"pregunta":pregunta,"aproximacion_suficiente":aproximacion,"evidencia_ideal":evidencia_ideal,"evidencia_necesaria":aproximacion}
        if answer:
            approximations.append({"tema":vacio,"estado":"Aproximación registrada","respuesta":answer[:1200],"alcance":"Es una base suficiente para decidir y aprender en un piloto; no se presenta como una certeza universal."})
        else:
            gaps.append(item)
    if "alfajor" in request or brief.get("motivations", "").strip() or brief.get("behavior", "").strip():
        add_gap("Motivación y comportamiento real de las personas","Sin conocer ocasión, disparador y barrera de compra no puede sostenerse una tensión humana ni un insight.","¿Quién compra, quién consume, en qué ocasión elige y por qué elegiría o descartaría esta propuesta?","Cruzar 3 comercios y 1 distribuidor con estudios o publicaciones sobre hábitos de snack, compra impulsiva y consumo de alfajores en Argentina y Uruguay.","Entrevistas a compradores y consumidores, observación en punto de venta y datos de ocasiones de consumo.","consumer_behavior_evidence")
    if "marca nueva" in request or "mantener" in request or not brief.get("positioning", "").strip():
        add_gap("Arquitectura y relación entre las marcas","Sin definir el vínculo entre marca nueva, marca histórica y fabricante existe riesgo de canibalización o confusión.","¿Qué debe representar cada marca, qué comparte con la otra y qué nunca debería compartir?","Acordar una regla operativa con el dueño, contrastarla con los 3 compradores actuales y revisar casos publicados de marcas regionales que lanzaron una segunda marca.","Decisión de arquitectura de marca, mapa de públicos y prueba de comprensión de nombres y respaldos.","brand_architecture")
    if any(token in request for token in ("precio", "pesos", "$", "1000", "650")):
        add_gap("Valor percibido y aceptación del precio","La diferencia de precio es una hipótesis comercial; comunicación no puede corregir una ecuación de valor no validada.","¿Qué atributos justifican el precio y cuánto están realmente dispuestos a pagar compradores y canales?","Relevar 10 puntos de venta y cruzarlo con estudios y publicaciones de inflación, consumo masivo, snack y compra por impulso; pedir opinión de precio a distribuidores y comercios.","Prueba de producto y precio, comparación por gramaje y margen, entrevistas con consumidores y comercios.","price_value_evidence")
    if any(token in commercial for token in ("crec", "produ", "unidad", "distrib", "venta", "100")):
        add_gap("Capacidad productiva y de distribución","La meta comercial puede fracasar aunque la comunicación funcione si producción, reposición y cobertura no acompañan.","¿Cuánta producción, distribución y reposición soporta hoy el negocio y qué inversión requiere la meta?","Armar una planilla simple por turno, lote, entrega y ruta con el responsable de fábrica y los distribuidores de Concordia, Chajarí y Concepción del Uruguay.","Capacidad instalada, costos, márgenes, puntos de venta actuales/potenciales y plan logístico por territorio.","capacity_distribution_evidence")
    audience=brief.get("audience", "")
    if not audience.strip() or len(audience.split())>12:
        add_gap("Priorización de audiencias","Una audiencia demasiado amplia mezcla comprador, consumidor y prescriptor, impidiendo elegir una conducta prioritaria.","¿Cuál es el segmento que destraba el crecimiento primero y qué papel cumplen los demás?","Definir un segmento inicial con distribuidores y comercios, usando ticket, ubicación, horario y tipo de compra; contrastarlo con estudios publicados de consumidores jóvenes y hogares.","Tamaño y valor de segmentos, frecuencia, poder de decisión y comportamiento de compra por segmento.","audience_priority_evidence")
    if brief.get("product", "").strip() or brief.get("competitors", "").strip():
        add_gap("Prueba competitiva y de producto","La historia y la calidad declarada son percepciones internas hasta compararlas con alternativas reales.","¿En qué dimensión concreta el producto gana, empata o pierde frente a cada competidor?","Hacer una mesa comparativa con 5 competidores, contrastarla con 2 comercios y sumar publicaciones sobre movimientos, lanzamientos y tendencias de la categoría.","Cata o prueba ciega, auditoría de precio/envase/exhibición y evidencia de rotación o recompra.","competitive_product_evidence")
    gaps=gaps[:6]
    top_names=[gap["vacio"] for gap in gaps[:3]]
    product=brief.get("product") or "la propuesta"
    positioning=brief.get("positioning") or product
    territory=brief.get("territory") or "el territorio inicial"
    proof=brief.get("proof") or "la credencial de origen y producto"
    brand_role=brief.get("brand_architecture") or "un rol propio para la nueva marca y un respaldo selectivo de la marca histórica"
    commercial_goal=brief.get("commercial_goal") or "el objetivo comercial declarado"
    is_launch=any(token in request for token in ("marca nueva", "lanz", "relanz"))
    has_commercial_friction=any(token in commercial for token in ("distrib", "venta", "unidad", "crec", "precio"))
    if is_launch and has_commercial_friction:
        recommended_route="Ruta 3 · Remover la fricción comercial"
        recommendation=(f"Priorizar una salida de lanzamiento acotada: presentar {project.name} como una propuesta individual para el consumo cotidiano, "
            f"con {proof} como salto de valor, y resolver primero disponibilidad, precio y exhibición. La relación de marca debe operar así: {brand_role}.")
        why_now=(f"El objetivo comercial ({commercial_goal}) depende más de llegar al canal y de ser elegible frente a alternativas existentes que de una campaña de notoriedad masiva.")
        first_move=(f"Diseñar un piloto en {territory}: definir precio y exhibición de entrada, acordar reposición con los compradores/distribuidores disponibles y medir unidades, rotación y recompra antes de ampliar cobertura.")
        no_do="No expandir territorio ni invertir primero en comunicación masiva hasta comprobar reposición, margen y aceptación del precio en el piloto."
    else:
        recommended_route="Ruta 1 · Reencuadrar la categoría"
        recommendation=f"Usar {positioning} para construir una propuesta de categoría más relevante, apoyada en {proof}, sin convertir una percepción interna en una promesa cerrada."
        why_now="La información disponible permite definir una hipótesis de posicionamiento, pero todavía no una ventaja concluyente frente a la competencia."
        first_move=f"Probar la propuesta en {territory} con los canales y públicos prioritarios, documentando las reacciones y la respuesta comercial."
        no_do="No cerrar una promesa definitiva ni multiplicar mensajes antes de registrar aprendizaje de la primera salida."
    routes=[
        {"nombre":"Reencuadrar la categoría","hipotesis":"Construir relevancia desde una tensión humana todavía por validar.","condicion_para_elegirla":gaps[0]["vacio"] if gaps else "La información cargada permite elegir una ruta de trabajo y contrastarla durante el piloto."},
        {"nombre":"Hacer visible una prueba superior","hipotesis":"Convertir una ventaja comprobable de producto u origen en preferencia.","condicion_para_elegirla":"Contrastar por aproximación la prueba competitiva y de producto."},
        {"nombre":"Remover la fricción comercial","hipotesis":"Alinear propuesta, precio, distribución y comunicación para facilitar la elección.","condicion_para_elegirla":"Contrastar por aproximación valor percibido y capacidad de distribución."},
    ]
    base={key:insufficient for key in DOSSIER_KEYS}
    base.update({
        "resumen_ejecutivo":{"lectura_actual":"El pedido combina crecimiento, construcción de marca y transformación comercial. La comunicación puede ayudar, pero todavía no está demostrado cuál es la barrera humana que debe resolver.","nivel_de_confianza":"Bajo: la mayor parte de la información proviene del brief y de referencias generales.","vacios_criticos":top_names},
        "pedido_original":brief.get("request") or project.brief or "No documentado.",
        "interpretacion_del_pedido":"Antes de lanzar comunicación hay que separar tres decisiones: viabilidad del crecimiento, arquitectura de marca y motivo real de elección.",
        "fuentes_y_calidad":{"fuentes":source_names or ["Brief inicial"],"evaluacion":"Las fuentes aportan contexto de categoría, pero no sustituyen evidencia propia de consumidores, canales, producto y operación.","aproximaciones_registradas":approximations or ["Todavía no se registraron aproximaciones específicas."]},
        "que_sabemos":[value for value in (brief.get("product"),brief.get("business_context"),project.objective) if value] or [insufficient],
        "que_creemos":["La marca histórica puede aportar confianza, pero también puede limitar la diferenciación de la nueva propuesta.","La meta de crecimiento exige resolver simultáneamente demanda, distribución y capacidad; no es solamente un problema de notoriedad."],
        "que_no_sabemos":gaps,
        "diagnostico_del_problema":{"hallazgo_preliminar":"El desafío parece ser construir una propuesta elegible y escalable, no solamente lanzar una marca.","hipotesis_a_refutar":"Si la gente conoce la nueva marca, la comprará al precio y en el canal propuestos.","por_que_no_es_conclusion":f"Antes de cerrar una ruta, conviene contrastar por aproximación: {', '.join(top_names)}." if top_names else "La base cargada permite elegir una ruta de trabajo. La hipótesis se contrasta durante el piloto con rotación, reposición, aceptación del precio y aprendizaje de canal."},
        "objetivos_diferenciados":{"negocio":brief.get("business_goal") or insufficient,"comercial":brief.get("commercial_goal") or insufficient,"comunicacion":brief.get("communication_goal") or project.objective or insufficient,"medios":brief.get("media_goal") or insufficient},
        "comportamiento_a_cambiar":brief.get("behavior") or {"pendiente":"Definir una sola conducta observable del segmento prioritario.","pregunta":gaps[0]["pregunta"] if gaps else "Definir la conducta prioritaria para el piloto."},
        "categoria_y_competencia":brief.get("competitors") or insufficient,
        "antecedentes_oliva":brief.get("previous_work") or insufficient,
        "audiencias":brief.get("audience") or insufficient,
        "barreras":brief.get("barriers") or insufficient,
        "tension_humana":{"estado":"Hipótesis a validar","formulacion_base":brief.get("motivations") or insufficient,"validacion_necesaria":gaps[0]["evidencia_necesaria"] if gaps else "Contrastar la hipótesis durante el piloto de lanzamiento."},
        "insight":{"estado":"Aún no validado","criterio":"Debe emerger de una contradicción comprobada entre deseo y conducta, no del pedido del cliente."},
        "oportunidad_estrategica":{"estado":"Hipótesis de trabajo","formulacion":"Hacer que origen, producto y acceso trabajen como una sola propuesta de valor.","condicion":f"Contrastar por aproximación: {', '.join(top_names)}." if top_names else insufficient},
        "rol_de_marca":{"estado":"Hipótesis de rol","respuesta_actual":brief.get("brand_architecture") or insufficient,"validacion_necesaria":"Confirmar que consumidores y canal comprendan la relación entre ambas marcas."},
        "promesa":{"estado":"Hipótesis de promesa","formulacion_base":brief.get("positioning") or brief.get("product") or insufficient,"decision_necesaria":"Elegir una promesa que supere la prueba de producto, precio y competencia."},
        "razones_para_creer":brief.get("proof") or insufficient,
        "tono":brief.get("brand_tone") or insufficient,
        "canales_y_contextos":{"territorio":brief.get("territory") or insufficient,"distribucion":brief.get("distribution") or insufficient,"medios":brief.get("media_goal") or insufficient},
        "ruta_1":routes[0],"ruta_2":routes[1],"ruta_3":routes[2],
        "comparacion_de_rutas":{"ruta_1":"Prioriza relevancia humana.","ruta_2":"Prioriza superioridad demostrable.","ruta_3":"Prioriza disponibilidad y reducción de fricción.","decision_pendiente":"Se puede elegir una ruta de trabajo con aproximaciones explícitas; no cerrarla como definitiva hasta aprender del lanzamiento."},
        "riesgos":["Confundir notoriedad con demanda.","Crear dos marcas sin roles claros.","Prometer crecimiento que producción o distribución no pueden sostener.","Definir una audiencia tan amplia que la comunicación pierda precisión."],
        "indicadores":brief.get("measurement") or {"negocio":"Margen y capacidad utilizada.","comercial":"Unidades, rotación, recompra y cobertura.","comunicacion":"Conocimiento, comprensión de propuesta y preferencia."},
        "preguntas_indispensables":[gap["pregunta"] for gap in gaps[:3]],
        "preguntas_importantes":[gap["pregunta"] for gap in gaps[3:]],
        "preguntas_deseables":["¿Qué aprendizajes de casos propios o premiados son transferibles sin copiar ejecuciones?"],
        "proxima_decision":{"recomendacion_estrategica":recommended_route,"por_que_ahora":why_now,"primer_movimiento":first_move,"no_hacer_aun":no_do,"decision_posible_ahora":"Se puede elegir una ruta de trabajo y avanzar con aproximaciones explícitas.","no_cerrar_aun":"No presentar las aproximaciones como certezas universales; revisarlas con ventas, reposición y aprendizaje del lanzamiento.","resolver_primero":top_names or ["Ejecutar el piloto y registrar qué confirma o refuta la hipótesis elegida."],"plan_de_validacion":[gap["aproximacion_suficiente"] for gap in gaps[:3]] or ["Medir respuesta, rotación, reposición y aprendizaje de la primera activación."],"criterio_de_salida":"Cuando estas aproximaciones estén documentadas, o cuando el piloto produzca nuevos hallazgos, generar una nueva versión y revisar la ruta de lanzamiento."},
    })
    return base
def analyze_dossier(project:Project,brief:dict[str,str],context:str,source_names:list[str])->tuple[dict[str,object],str]:
    s=get_settings()
    if not s.openai_api_key:return local_dossier(project,brief,source_names),"OLIVA Strategy — modo local"
    try:
        inp=json.dumps({"proyecto":project.name,"objetivo":project.objective,"brief":brief,"fuentes":source_names,"contenido":context[:120000]},ensure_ascii=False);text,model=responses_text({"model":s.openai_strategy_model,"instructions":MASTER_PROMPT,"input":inp,"text":{"format":{"type":"json_object"}}});data=json.loads(text or "{}");fallback=local_dossier(project,brief,source_names);return {k:data.get(k,fallback[k]) for k in DOSSIER_KEYS},model
    except Exception:
        return local_dossier(project,brief,source_names),"OLIVA Strategy — modo local (API no disponible)"
def analyze(project:Project,document_text:str,client_context:str="")->dict[str,str]:
    s=get_settings();context=f"Proyecto: {project.name}\nCliente: {client_context}\nObjetivo: {project.objective}\nBrief: {project.brief}\nFuentes: {document_text[:70000]}"
    if s.openai_api_key:
        try:
            response=OpenAI(api_key=s.openai_api_key).chat.completions.create(model=s.openai_strategy_model,response_format={"type":"json_object"},messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":context}]);data=json.loads(response.choices[0].message.content or "{}");data["model_used"]=s.openai_strategy_model;return data
        except Exception:
            pass
    has=bool(document_text.strip());return {"diagnosis":"El desafío declarado necesita validarse contra comportamiento, negocio y personas.","evidence":"Se incorporaron fuentes." if has else "La evidencia se limita al brief.","hypotheses":"Puede existir una brecha entre percepción interna y motivaciones reales.","contradictions":"Aún no hay evidencia suficiente para identificar contradicciones robustas.","strategic_question":"¿Qué comportamiento debe cambiar, en quién, y qué evidencia demuestra la barrera?","confidence":"media" if has else "baja","model_used":"OLIVA Strategy — modo local (API no disponible)" if s.openai_api_key else "OLIVA Strategy — modo local"}
