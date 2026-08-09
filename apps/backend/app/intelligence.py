import base64,json
from pathlib import Path
from .config import get_settings
from .documents import extract_text
from .strategy import response_text,responses_payload,responses_text
FESTIVAL_DOMAINS=["canneslions.com","dandad.org","oneclub.org","clios.com","effie.org"]
SCORE_KEYS=["estrategia","verdad_humana","rol_de_marca","apropiabilidad","originalidad","claridad","fertilidad","coherencia","adecuacion_al_medio","viabilidad"]
def festival_research(query:str)->tuple[str,list[dict[str,str]],str]:
    s=get_settings()
    if not s.openai_api_key:return "La búsqueda automática requiere configurar OPENAI_API_KEY. Podés guardar enlaces manualmente.",[],"modo local"
    b=responses_payload({"model":s.openai_search_model,"tools":[{"type":"web_search","filters":{"allowed_domains":FESTIVAL_DOMAINS},"search_context_size":"medium"}],"tool_choice":"required","include":["web_search_call.action.sources"],"input":f"Buscá casos premiados relevantes para: {query}. Priorizá resultados comprobables y explicá el aprendizaje estratégico. Citá las fuentes."});sources=[];seen=set()
    for o in b.get("output",[]):
        for x in (o.get("action") or {}).get("sources",[]):
            u=x.get("url","")
            if u and u not in seen:seen.add(u);sources.append({"title":x.get("title") or u,"url":u})
        for c in o.get("content",[]):
            for x in c.get("annotations",[]):
                u=x.get("url","")
                if x.get("type")=="url_citation" and u and u not in seen:seen.add(u);sources.append({"title":x.get("title") or u,"url":u})
    return response_text(b),sources,b.get("model",s.openai_search_model)
CREATIVE_PROMPT="""Sos el comité creativo de OLIVA. Evaluá contra la estrategia aprobada y contexto de marca. No premies estética sin estrategia. Aplicá sustitución de logo, cambio de categoría y eliminación de estética. Puntúa 0-5 estrategia, verdad_humana, rol_de_marca, apropiabilidad, originalidad, claridad, fertilidad, coherencia, adecuacion_al_medio, viabilidad. Las primeras críticas son estrategia, coherencia y apropiabilidad. Respondé SOLO JSON: verdict (aprobable/revisar/no_alineada), scores y evaluation concreta."""
def evaluate_creative(path:Path,content_type:str,name:str,medium:str,rationale:str,strategy:dict,brand_context:str)->dict:
    s=get_settings()
    if not s.openai_api_key:return {"verdict":"pending","scores":{k:0 for k in SCORE_KEYS},"evaluation":"La pieza quedó guardada. Configurá OPENAI_API_KEY para recibir devolución automática.","model_used":"OLIVA Creative Review — modo local"}
    raw=path.read_bytes();content=[{"type":"input_text","text":json.dumps({"nombre":name,"medio":medium,"fundamento":rationale,"estrategia":strategy,"marca":brand_context},ensure_ascii=False)}]
    if content_type.startswith("image/"):content.append({"type":"input_image","image_url":f"data:{content_type};base64,{base64.b64encode(raw).decode()}","detail":"high"})
    else:content.append({"type":"input_text","text":extract_text(raw,content_type)[:60000]})
    text,model=responses_text({"model":s.openai_vision_model,"instructions":CREATIVE_PROMPT,"input":[{"role":"user","content":content}],"text":{"format":{"type":"json_object"}}});data=json.loads(text or "{}");data["model_used"]=model;data["scores"]={k:int(data.get("scores",{}).get(k,0)) for k in SCORE_KEYS};return data
