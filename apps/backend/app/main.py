from contextlib import asynccontextmanager
import base64
import json
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from .auth import create_token, current_user, hash_password, verify_password
from .config import get_settings
from .database import create_db_and_tables, get_session
from .documents import ALLOWED, MAX_SIZE, extract_text, safe_name
from .ingestion import AUDIO_EXTENSIONS, AUDIO_MAX_SIZE, AUDIO_TYPES, EMAIL_MAX_SIZE, extract_email, format_email, transcribe_audio
from .knowledge import PHOTO_MAX_SIZE, PHOTO_TYPES, analyze_photo, embed_text, index_text, radar_context, relevant_matches
from .link_reader import read_link
from .models import AgentRun, ApprovalTask, BrandAsset, Client, ClientMemory, CreativeAnnotation, CreativeConcept, CreativeNote, CreativeProductionPlan, CreativeSubmission, CreativeVisualDraft, Document, EvidenceItem, KnowledgeItem, KnowledgeKind, KnowledgeVector, LearningRecord, LibraryEntry, MarketWatch, MeasurementRecord, Project, ProjectBrief, ProjectKnowledgeLink, ProjectRadarVector, ProjectStatus, ProjectTask, RadarLinkStatus, ResearchSource, StrategyDecision, StrategyDossier, StrategyResult, User, now
from .schemas import AgentDefinitionOut, AgentRunIn, AgentRunOut, ApprovalIn, ApprovalResolveIn, ApprovalTaskOut, BrandAssetOut, BriefIn, BriefOut, ClientIn, ClientMemoryIn, ClientMemoryOut, ClientOut, ClientUpdateIn, CreativeAnnotationIn, CreativeAnnotationOut, CreativeAnnotationUpdateIn, CreativeConceptGenerateIn, CreativeConceptOut, CreativeConceptUpdateIn, CreativeNoteIn, CreativeNoteOut, CreativeNoteUpdateIn, CreativeOut, CreativeProductionPlanOut, CreativeProductionPlanUpdateIn, CreativeTableIn, CreativeVisualGenerateIn, CreativeVisualOut, CreativeVisualUpdateIn, DocumentOut, DocumentTextIn, DossierOut, EmailTextIn, EvidenceIn, FestivalSearchIn, KnowledgeLinkIn, KnowledgeOut, LearningRecordIn, LearningRecordOut, LibraryLinkIn, LibraryOut, LoginIn, MarketWatchIn, MarketWatchOut, MarketWatchUpdateIn, MeasurementIn, MeasurementOut, ProductionPackageOut, ProjectIn, ProjectOut, ProjectResearchIn, ProjectResearchOut, ProjectTaskIn, ProjectTaskOut, ProjectTaskUpdateIn, ProjectUpdateIn, RadarDecisionIn, RadarSuggestionOut, RegisterIn, ResearchSourceIn, ResearchSourceOut, ResearchSourceUpdateIn, StrategyDecisionIn, StrategyDecisionOut, TokenOut, UserOut, UserUpdateIn
from .strategy import analyze, analyze_dossier, local_dossier
from .intelligence import creative_table, evaluate_creative, festival_research, generate_campaign_plan, generate_creative_concepts, generate_production_proposals, project_web_research, run_agent
from .foundations import AGENT_CATALOG, CREATIVE_REFERENCE_LENSES, FESTIVAL_CATALOG, FOUNDATIONAL_REFERENCES, foundational_context
from .research_sources import DEFAULT_RESEARCH_SOURCES, source_payload

settings = get_settings()


def save_knowledge_vector(item: KnowledgeItem, session: Session) -> None:
    try:
        vector = embed_text(item.indexed_text or index_text(item))
    except Exception:
        vector = None
    if not vector:
        return
    stored = session.exec(select(KnowledgeVector).where(KnowledgeVector.knowledge_item_id == item.id)).first()
    if stored:
        stored.embedding_json = json.dumps(vector); stored.model = settings.openai_embedding_model; stored.updated_at = now()
    else:
        stored = KnowledgeVector(knowledge_item_id=item.id, embedding_json=json.dumps(vector), model=settings.openai_embedding_model)
    session.add(stored); session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.post("/api/auth/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.email == data.email.lower())).first():
        raise HTTPException(409, "El email ya está registrado")
    user = User(email=data.email.lower(), name=data.name, password_hash=hash_password(data.password))
    session.add(user); session.commit(); session.refresh(user)
    return TokenOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@app.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email.lower())).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")
    return TokenOut(access_token=create_token(user.id), user=UserOut.model_validate(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.patch("/api/auth/me", response_model=UserOut)
def update_me(data: UserUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if data.new_password:
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(400, "La contraseña actual no es correcta")
        user.password_hash = hash_password(data.new_password)
    user.name = data.name.strip()
    session.add(user); session.commit(); session.refresh(user)
    return user


@app.get("/api/clients", response_model=list[ClientOut])
def list_clients(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return session.exec(select(Client).where(Client.owner_id == user.id).order_by(Client.created_at.desc())).all()


@app.post("/api/clients", response_model=ClientOut, status_code=201)
def create_client(data: ClientIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    client = Client(**data.model_dump(), owner_id=user.id)
    session.add(client); session.commit(); session.refresh(client)
    return client


def owned_client(client_id: UUID, user: User, session: Session) -> Client:
    client = session.get(Client, client_id)
    if not client or client.owner_id != user.id:
        raise HTTPException(404, "Cliente no encontrado")
    return client


MEMORY_FIELDS = ("history", "products", "audiences", "competitors", "positioning", "tone", "visual_codes", "restrictions", "approved_patterns", "rejected_patterns", "commercial_context", "territories", "notes")

# Estándar permanente de la etapa de diseño OLIVA. Funciona como criterio de
# dirección de arte, no como una estética prefabricada ni una imitación de autores.
OLIVA_ART_DIRECTION_STANDARD = """
Act as an internationally experienced senior art director. First think, then reduce,
then design, then self-critique before delivering. The image must communicate a clear
visual idea, contemporary sophistication, personality, hierarchy, craft and a decision
behind every element; never an AI-generated sketch, social template or decorative collage.
Build one visual concept strong enough to become a campaign system. Use editorial
composition: deliberate grid, proportion, tension, scale, contrast, negative space and a
single unequivocal visual entry point. Avoid automatic centering, obvious symmetry,
floating elements, gratuitous backgrounds and excess information.
Photography must feel art-directed, credible and materially real: coherent light, natural
proportions, authentic texture, considered casting/styling/scouting and professional post.
Avoid plastic perfection, generic stock imagery, arbitrary cinematic light, gratuitous
gradients, neon, 3D, fake interfaces, icons, excessive effects, decorative transparency,
and any Canva-like layout. Less elements, better decisions.
Seek one unexpected, intelligent and memorable art-direction decision that makes the idea
recognizable without sacrificing clarity, effectiveness or real-world adaptability.
Use the level of reduction, craft and critical rigor associated with major international
creative and design annuals, without copying a campaign, studio or designer. Do not imitate
any living artist. Before delivery reject the image if it could belong to any brand or if
any element can be removed to make it stronger. No text, typography, letters, logos or
claims are permitted inside this generated raster: the OLIVA interface applies real brand
assets and controlled typography separately.
"""


def memory_output(memory: ClientMemory) -> ClientMemoryOut:
    return ClientMemoryOut(id=memory.id, client_id=memory.client_id, data=json.loads(memory.data_json), version=memory.version, updated_at=memory.updated_at)


def brand_asset_output(asset: BrandAsset) -> BrandAssetOut:
    return BrandAssetOut(id=asset.id, client_id=asset.client_id, label=asset.label, filename=asset.filename, content_type=asset.content_type, size=asset.size, palette=asset.palette, created_at=asset.created_at)


def learning_output(record: LearningRecord) -> LearningRecordOut:
    return LearningRecordOut(id=record.id, project_id=record.project_id, client_id=record.client_id, title=record.title, content=record.content, source_type=record.source_type, tags=record.tags, confidence=record.confidence, status=record.status, evidence=json.loads(record.evidence_json), created_at=record.created_at, updated_at=record.updated_at)


def agent_run_output(run: AgentRun) -> AgentRunOut:
    return AgentRunOut(id=run.id, project_id=run.project_id, agent_key=run.agent_key, instruction=run.instruction, output=json.loads(run.output_json), status=run.status, model_used=run.model_used, created_at=run.created_at)


def research_source_output(source: ResearchSource) -> ResearchSourceOut:
    return ResearchSourceOut.model_validate(source)


def ensure_research_sources(user: User, session: Session) -> list[ResearchSource]:
    sources = session.exec(select(ResearchSource).where(ResearchSource.owner_id == user.id)).all()
    if sources:
        return sources
    for row in DEFAULT_RESEARCH_SOURCES:
        session.add(ResearchSource(owner_id=user.id, is_foundational=True, **source_payload(row)))
    session.commit()
    return session.exec(select(ResearchSource).where(ResearchSource.owner_id == user.id)).all()


def active_research_domains(user: User, session: Session) -> list[str]:
    sources = ensure_research_sources(user, session)
    active = sorted((source for source in sources if source.active), key=lambda source: (source.priority, source.country, source.name))
    return list(dict.fromkeys(source.domain for source in active))[:90]


def create_approval_task(session: Session, user: User, project_id: UUID | None, kind: str, entity_id: str, title: str, summary: str) -> ApprovalTask:
    existing = session.exec(select(ApprovalTask).where(ApprovalTask.owner_id == user.id, ApprovalTask.kind == kind, ApprovalTask.entity_id == entity_id, ApprovalTask.status == "pending")).first()
    if existing:
        existing.title = title; existing.summary = summary; session.add(existing); return existing
    task = ApprovalTask(owner_id=user.id, project_id=project_id, kind=kind, entity_id=entity_id, title=title, summary=summary)
    session.add(task)
    return task


def relevant_learning_records(project: Project, user: User, session: Session, limit: int = 8) -> list[LearningRecord]:
    records = session.exec(select(LearningRecord).where(LearningRecord.owner_id == user.id, LearningRecord.status == "approved")).all()
    reference = f"{project.name} {project.objective} {project.brief}".lower()
    terms = {term for term in reference.replace("/", " ").split() if len(term) >= 4}
    ranked: list[tuple[int, LearningRecord]] = []
    for record in records:
        if record.client_id and record.client_id != project.client_id:
            continue
        text = f"{record.title} {record.content} {record.tags}".lower()
        score = (70 if record.project_id == project.id else 35 if record.client_id == project.client_id else 0) + sum(term in text for term in terms) * 10
        if score:
            ranked.append((score, record))
    return [record for _, record in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]


@app.patch("/api/clients/{client_id}", response_model=ClientOut)
def update_client(client_id: UUID, data: ClientUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    client = owned_client(client_id, user, session)
    for key, value in data.model_dump().items():
        setattr(client, key, value.strip())
    session.add(client); session.commit(); session.refresh(client)
    return client


@app.get("/api/clients/{client_id}/memory", response_model=ClientMemoryOut)
def get_client_memory(client_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    client = owned_client(client_id, user, session)
    memory = session.exec(select(ClientMemory).where(ClientMemory.client_id == client.id)).first()
    if not memory:
        memory = ClientMemory(client_id=client.id, owner_id=user.id, data_json=json.dumps({key: "" for key in MEMORY_FIELDS}))
        session.add(memory); session.commit(); session.refresh(memory)
    return memory_output(memory)


@app.put("/api/clients/{client_id}/memory", response_model=ClientMemoryOut)
def save_client_memory(client_id: UUID, data: ClientMemoryIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    client = owned_client(client_id, user, session)
    clean = {str(key): str(value).strip() for key, value in data.data.items() if str(key) in MEMORY_FIELDS}
    memory = session.exec(select(ClientMemory).where(ClientMemory.client_id == client.id)).first()
    if memory:
        memory.data_json = json.dumps(clean, ensure_ascii=False); memory.version += 1; memory.updated_at = now()
    else:
        memory = ClientMemory(client_id=client.id, owner_id=user.id, data_json=json.dumps(clean, ensure_ascii=False))
    session.add(memory); session.commit(); session.refresh(memory)
    return memory_output(memory)


@app.get("/api/clients/{client_id}/brand-assets", response_model=list[BrandAssetOut])
def list_brand_assets(client_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_client(client_id, user, session)
    return [brand_asset_output(asset) for asset in session.exec(select(BrandAsset).where(BrandAsset.client_id == client_id, BrandAsset.owner_id == user.id).order_by(BrandAsset.created_at.desc())).all()]


@app.post("/api/clients/{client_id}/brand-assets", response_model=BrandAssetOut, status_code=201)
async def upload_brand_asset(client_id: UUID, file: UploadFile = File(...), label: str = Form(default="Logo de marca", max_length=160), palette: str = Form(default="", max_length=500), user: User = Depends(current_user), session: Session = Depends(get_session)):
    client = owned_client(client_id, user, session)
    content_type = file.content_type or "application/octet-stream"
    if content_type not in PHOTO_TYPES:
        raise HTTPException(415, "Subí un logo PNG, JPG o WEBP")
    raw = await file.read(PHOTO_MAX_SIZE + 1)
    if len(raw) > PHOTO_MAX_SIZE:
        raise HTTPException(413, "El logo supera 10 MB")
    filename = safe_name(file.filename or "logo")
    asset = BrandAsset(client_id=client.id, owner_id=user.id, label=label.strip() or "Logo de marca", filename=filename, storage_path="", content_type=content_type, size=len(raw), palette=palette.strip())
    path = Path(settings.upload_dir) / "brands" / str(client.id) / f"{asset.id}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw); asset.storage_path = str(path)
    session.add(asset); session.commit(); session.refresh(asset)
    return brand_asset_output(asset)


@app.get("/api/clients/{client_id}/brand-assets/{asset_id}/media")
def brand_asset_media(client_id: UUID, asset_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_client(client_id, user, session)
    asset = session.get(BrandAsset, asset_id)
    if not asset or asset.client_id != client_id or asset.owner_id != user.id or not Path(asset.storage_path).exists():
        raise HTTPException(404, "Logo no encontrado")
    return FileResponse(asset.storage_path, media_type=asset.content_type, filename=asset.filename)


@app.delete("/api/clients/{client_id}", status_code=204)
def delete_client(client_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    client = owned_client(client_id, user, session)
    if session.exec(select(Project).where(Project.client_id == client.id)).first():
        raise HTTPException(409, "Este cliente tiene proyectos. Eliminá o reasigná esos proyectos primero.")
    for asset in session.exec(select(BrandAsset).where(BrandAsset.client_id == client.id)).all():
        if asset.storage_path: Path(asset.storage_path).unlink(missing_ok=True)
        session.delete(asset)
    session.delete(client); session.commit()


@app.get("/api/knowledge", response_model=list[KnowledgeOut])
def list_knowledge(q: str = Query(default="", max_length=200), user: User = Depends(current_user), session: Session = Depends(get_session)):
    items = session.exec(select(KnowledgeItem).where(KnowledgeItem.owner_id == user.id).order_by(KnowledgeItem.created_at.desc())).all()
    if not q.strip():
        return items
    terms = q.lower().split()
    return [item for item in items if all(term in (item.indexed_text or index_text(item)).lower() for term in terms)]


@app.post("/api/knowledge/links", response_model=KnowledgeOut, status_code=201)
def add_knowledge_link(data: KnowledgeLinkIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    values = data.model_dump(); values["url"] = str(values["url"])
    try:
        page = read_link(values["url"], include_body=data.kind == KnowledgeKind.article)
    except Exception:
        page = {"title": "", "source": "", "description": "", "text": "", "final_url": values["url"]}
    values["url"] = page.get("final_url") or values["url"]
    values["title"] = values["title"].strip() or page.get("title") or urlparse(values["url"]).hostname or "Referencia sin título"
    if not values["source"]:
        values["source"] = page.get("source", "")
    item = KnowledgeItem(
        **values,
        owner_id=user.id,
        ai_summary=data.notes or page.get("description", ""),
        ai_observations="Contenido web leído e indexado automáticamente." if page.get("text") else "Lectura automática pendiente; se indexaron los datos aportados.",
        index_status="indexed" if page.get("text") else "manual",
    )
    item.indexed_text = f"{index_text(item)} {page.get('title', '')} {page.get('text', '')}".strip()
    session.add(item); session.commit(); session.refresh(item)
    save_knowledge_vector(item, session)
    return item


@app.post("/api/knowledge/photos", response_model=KnowledgeOut, status_code=201)
async def add_knowledge_photo(
    file: UploadFile = File(...), title: str = Form(..., min_length=2, max_length=250),
    source: str = Form(default="", max_length=250), notes: str = Form(default="", max_length=20000),
    tags: str = Form(default="", max_length=1000), user: User = Depends(current_user), session: Session = Depends(get_session),
):
    content_type = file.content_type or "application/octet-stream"
    if content_type not in PHOTO_TYPES:
        raise HTTPException(415, "Formato no admitido. Usá JPG, PNG o WEBP.")
    data = await file.read(PHOTO_MAX_SIZE + 1)
    if len(data) > PHOTO_MAX_SIZE:
        raise HTTPException(413, "La foto supera 15 MB")
    item = KnowledgeItem(kind=KnowledgeKind.photo, title=title, source=source, notes=notes, tags=tags, content_type=content_type, size=len(data), owner_id=user.id)
    path = Path(settings.upload_dir) / "knowledge" / str(user.id) / f"{item.id}_{safe_name(file.filename or 'foto')}"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); item.storage_path = str(path)
    try:
        visual = analyze_photo(data, content_type, title, notes)
    except Exception:
        visual = {"ai_summary": notes or "Foto guardada; el análisis visual no pudo completarse.", "ai_observations": "Análisis visual pendiente.", "index_status": "failed"}
    for key, value in visual.items(): setattr(item, key, value)
    item.indexed_text = index_text(item)
    session.add(item); session.commit(); session.refresh(item)
    save_knowledge_vector(item, session)
    return item


def owned_knowledge(item_id: UUID, user: User, session: Session) -> KnowledgeItem:
    item = session.get(KnowledgeItem, item_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(404, "Elemento del Radar no encontrado")
    return item


@app.post("/api/knowledge/{item_id}/reindex", response_model=KnowledgeOut)
def reindex_knowledge(item_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    item = owned_knowledge(item_id, user, session)
    if item.kind == KnowledgeKind.photo:
        if not item.storage_path or not Path(item.storage_path).exists():
            raise HTTPException(404, "Foto no encontrada")
        try:
            visual = analyze_photo(Path(item.storage_path).read_bytes(), item.content_type, item.title, item.notes)
            for key, value in visual.items(): setattr(item, key, value)
        except Exception:
            item.index_status = "failed"; item.ai_observations = "Análisis visual pendiente."
    else:
        try:
            page = read_link(item.url, include_body=item.kind == KnowledgeKind.article)
            item.url = page.get("final_url") or item.url
            item.source = item.source or page.get("source", "")
            item.ai_summary = item.notes or page.get("description", "")
            item.ai_observations = "Contenido web leído e indexado automáticamente."
            item.index_status = "indexed"
            item.indexed_text = f"{index_text(item)} {page.get('title', '')} {page.get('text', '')}".strip()
        except Exception:
            item.index_status = "failed"; item.ai_observations = "No se pudo volver a leer el enlace."
    if item.kind == KnowledgeKind.photo:
        item.indexed_text = index_text(item)
    session.add(item); session.commit(); session.refresh(item)
    save_knowledge_vector(item, session)
    return item


@app.get("/api/knowledge/{item_id}/media")
def knowledge_media(item_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    item = owned_knowledge(item_id, user, session)
    if item.kind != KnowledgeKind.photo or not item.storage_path or not Path(item.storage_path).exists():
        raise HTTPException(404, "Foto no encontrada")
    return FileResponse(item.storage_path, media_type=item.content_type)


@app.delete("/api/knowledge/{item_id}", status_code=204)
def delete_knowledge(item_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    item = owned_knowledge(item_id, user, session)
    if item.storage_path:
        Path(item.storage_path).unlink(missing_ok=True)
    for link in session.exec(select(ProjectKnowledgeLink).where(ProjectKnowledgeLink.knowledge_item_id == item.id)).all(): session.delete(link)
    vector = session.exec(select(KnowledgeVector).where(KnowledgeVector.knowledge_item_id == item.id)).first()
    if vector: session.delete(vector)
    session.delete(item); session.commit()

LIBRARY_KINDS={"internal_case","visual_reference","brand_guide","learning","award_research"}
def owned_library(item_id:UUID,user:User,session:Session)->LibraryEntry:
    item=session.get(LibraryEntry,item_id)
    if not item or item.owner_id!=user.id:raise HTTPException(404,"Elemento de biblioteca no encontrado")
    return item
@app.get("/api/library",response_model=list[LibraryOut])
def list_library(kind:str=Query(default=""),user:User=Depends(current_user),session:Session=Depends(get_session)):
    items=session.exec(select(LibraryEntry).where(LibraryEntry.owner_id==user.id).order_by(LibraryEntry.created_at.desc())).all();return [i for i in items if not kind or i.kind==kind]
@app.post("/api/library/links",response_model=LibraryOut,status_code=201)
def add_library_link(data:LibraryLinkIn,user:User=Depends(current_user),session:Session=Depends(get_session)):
    if data.kind not in LIBRARY_KINDS:raise HTTPException(422,"Tipo inválido")
    if data.client_id:owned_client(data.client_id,user,session)
    url=str(data.url)
    try:page=read_link(url,include_body=True)
    except Exception:page={"title":"","source":"","description":"","text":"","final_url":url}
    item=LibraryEntry(kind=data.kind,title=page.get("title") or urlparse(url).hostname or "Referencia",url=page.get("final_url") or url,source=page.get("source") or urlparse(url).hostname or "",description=data.description or page.get("description",""),tags=data.tags,results=data.results,client_id=data.client_id,ai_analysis=(page.get("text") or "")[:30000],owner_id=user.id);session.add(item);session.commit();session.refresh(item);return item
@app.post("/api/library/files",response_model=LibraryOut,status_code=201)
async def add_library_file(file:UploadFile=File(...),kind:str=Form(...),description:str=Form(default="",max_length=20000),tags:str=Form(default="",max_length=1000),client_id:str=Form(default=""),user:User=Depends(current_user),session:Session=Depends(get_session)):
    if kind not in LIBRARY_KINDS:raise HTTPException(422,"Tipo inválido")
    ct=file.content_type or "application/octet-stream"
    if ct not in set(ALLOWED)|PHOTO_TYPES:raise HTTPException(415,"Usá PDF, Word, texto, JPG, PNG o WEBP")
    raw=await file.read(MAX_SIZE+1)
    if len(raw)>MAX_SIZE:raise HTTPException(413,"El archivo supera 15 MB")
    cid=UUID(client_id) if client_id else None
    if cid:owned_client(cid,user,session)
    filename=safe_name(file.filename or "referencia");item=LibraryEntry(kind=kind,title=Path(filename).stem.replace("_"," "),description=description,tags=tags,client_id=cid,content_type=ct,size=len(raw),owner_id=user.id);path=Path(settings.upload_dir)/"library"/str(user.id)/f"{item.id}_{filename}";path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);item.storage_path=str(path)
    if ct in PHOTO_TYPES:
        try:v=analyze_photo(raw,ct,item.title,description);item.ai_analysis=f"{v.get('ai_summary','')}\n{v.get('ai_observations','')}".strip()
        except Exception:item.ai_analysis="Referencia visual guardada; análisis pendiente."
    else:
        try:item.ai_analysis=extract_text(raw,ct)[:30000]
        except Exception:item.ai_analysis="Archivo guardado; extracción pendiente."
    session.add(item);session.commit();session.refresh(item);return item
@app.post("/api/library/festivals",response_model=list[LibraryOut],status_code=201)
def search_festival_cases(data:FestivalSearchIn,user:User=Depends(current_user),session:Session=Depends(get_session)):
    summary,sources,model=festival_research(data.query);records=[]
    for source in sources[:12]:
        item=LibraryEntry(kind="award_research",title=source["title"],url=source["url"],source=urlparse(source["url"]).hostname or "Festival",description=f"Investigación: {data.query}",ai_analysis=summary,tags="premios, festival",owner_id=user.id);session.add(item);records.append(item)
    if not records:item=LibraryEntry(kind="award_research",title=f"Investigación: {data.query}",description=data.query,ai_analysis=summary,source=model,owner_id=user.id);session.add(item);records.append(item)
    session.commit()
    for i in records:session.refresh(i)
    return records
@app.get("/api/library/{item_id}/media")
def library_media(item_id:UUID,user:User=Depends(current_user),session:Session=Depends(get_session)):
    item=owned_library(item_id,user,session)
    if not item.storage_path or not Path(item.storage_path).exists():raise HTTPException(404,"Archivo no encontrado")
    return FileResponse(item.storage_path,media_type=item.content_type)
@app.delete("/api/library/{item_id}",status_code=204)
def delete_library(item_id:UUID,user:User=Depends(current_user),session:Session=Depends(get_session)):
    item=owned_library(item_id,user,session)
    if item.storage_path:Path(item.storage_path).unlink(missing_ok=True)
    session.delete(item);session.commit()


@app.get("/api/foundations")
def foundations(user: User = Depends(current_user)):
    return {
        "references": FOUNDATIONAL_REFERENCES,
        "creative_lenses": CREATIVE_REFERENCE_LENSES,
        "festivals": FESTIVAL_CATALOG,
        "principle": "Las referencias metodológicas y creativas orientan el criterio. No se presentan como evidencia de un cliente, no imitan estilos personales ni sustituyen investigación situada.",
    }


@app.get("/api/library/festivals/catalog")
def festival_catalog(user: User = Depends(current_user)):
    return FESTIVAL_CATALOG


@app.get("/api/research-sources", response_model=list[ResearchSourceOut])
def list_research_sources(user: User = Depends(current_user), session: Session = Depends(get_session)):
    sources = ensure_research_sources(user, session)
    return [research_source_output(source) for source in sorted(sources, key=lambda source: (not source.active, source.priority, source.country, source.name))]


@app.post("/api/research-sources", response_model=ResearchSourceOut, status_code=201)
def create_research_source(data: ResearchSourceIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    ensure_research_sources(user, session)
    values = data.model_dump(); values["url"] = str(values["url"]); values["domain"] = urlparse(values["url"]).hostname.lower().removeprefix("www.")
    if session.exec(select(ResearchSource).where(ResearchSource.owner_id == user.id, ResearchSource.url == values["url"])).first():
        raise HTTPException(409, "Esta fuente ya está en la Biblioteca Cognitiva")
    source = ResearchSource(owner_id=user.id, is_foundational=False, **values)
    session.add(source); session.commit(); session.refresh(source)
    return research_source_output(source)


@app.patch("/api/research-sources/{source_id}", response_model=ResearchSourceOut)
def update_research_source(source_id: UUID, data: ResearchSourceUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    source = session.get(ResearchSource, source_id)
    if not source or source.owner_id != user.id:
        raise HTTPException(404, "Fuente no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(source, key, value.strip() if isinstance(value, str) else value)
    session.add(source); session.commit(); session.refresh(source)
    return research_source_output(source)


@app.delete("/api/research-sources/{source_id}", status_code=204)
def delete_research_source(source_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    source = session.get(ResearchSource, source_id)
    if not source or source.owner_id != user.id:
        raise HTTPException(404, "Fuente no encontrada")
    if source.is_foundational:
        source.active = False; session.add(source)
    else:
        session.delete(source)
    session.commit()


def watch_output(watch: MarketWatch) -> MarketWatchOut:
    return MarketWatchOut(id=watch.id, client_id=watch.client_id, name=watch.name, query=watch.query, kind=watch.kind, active=watch.active, last_summary=watch.last_summary, last_sources=json.loads(watch.last_sources_json), last_checked_at=watch.last_checked_at, created_at=watch.created_at)


@app.get("/api/watches", response_model=list[MarketWatchOut])
def list_watches(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return [watch_output(watch) for watch in session.exec(select(MarketWatch).where(MarketWatch.owner_id == user.id).order_by(MarketWatch.last_checked_at.desc())).all()]


@app.post("/api/watches", response_model=MarketWatchOut, status_code=201)
def create_watch(data: MarketWatchIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if data.client_id: owned_client(data.client_id, user, session)
    watch = MarketWatch(owner_id=user.id, **data.model_dump())
    session.add(watch); session.commit(); session.refresh(watch)
    return watch_output(watch)


@app.post("/api/watches/{watch_id}/run", response_model=MarketWatchOut)
def run_watch(watch_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    watch = session.get(MarketWatch, watch_id)
    if not watch or watch.owner_id != user.id: raise HTTPException(404, "Monitor no encontrado")
    summary, sources, _ = project_web_research(watch.name, "Inteligencia competitiva y de categoría", watch.query, active_research_domains(user, session))
    if not settings.openai_api_key: raise HTTPException(409, summary)
    watch.last_summary = summary; watch.last_sources_json = json.dumps(sources, ensure_ascii=False); watch.last_checked_at = now(); session.add(watch); session.commit(); session.refresh(watch)
    return watch_output(watch)


@app.patch("/api/watches/{watch_id}", response_model=MarketWatchOut)
def update_watch(watch_id: UUID, data: MarketWatchUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    watch = session.get(MarketWatch, watch_id)
    if not watch or watch.owner_id != user.id: raise HTTPException(404, "Monitor no encontrado")
    if data.active is not None: watch.active = data.active
    session.add(watch); session.commit(); session.refresh(watch); return watch_output(watch)


@app.get("/api/governance")
def governance(user: User = Depends(current_user), session: Session = Depends(get_session)):
    agent_runs = session.exec(select(AgentRun).where(AgentRun.owner_id == user.id)).all()
    visuals = session.exec(select(CreativeVisualDraft).where(CreativeVisualDraft.owner_id == user.id)).all()
    learning = session.exec(select(LearningRecord).where(LearningRecord.owner_id == user.id, LearningRecord.status == "approved")).all()
    return {"models": {"estrategia": settings.openai_strategy_model, "creatividad": settings.openai_creative_model, "operaciones": settings.openai_operations_model, "busqueda": settings.openai_search_model, "vision": settings.openai_vision_model}, "audit": {"agentes_ejecutados": len(agent_runs), "bocetos_generados": len(visuals), "aprendizajes_aprobados": len(learning)}, "controls": ["Cada salida informa el modelo usado y permanece trazable en el proyecto.", "Los aprendizajes pasan por aprobación humana antes de reutilizarse.", "Las fuentes externas se guardan con enlace y no se confunden con evidencia del cliente.", "La IA no puede aprobar estrategia, pieza o resultado en nombre del equipo."], "api_configured": bool(settings.openai_api_key)}


@app.get("/api/learning", response_model=list[LearningRecordOut])
def list_learning(project_id: UUID | None = None, client_id: UUID | None = None, status_filter: str = Query(default=""), user: User = Depends(current_user), session: Session = Depends(get_session)):
    records = session.exec(select(LearningRecord).where(LearningRecord.owner_id == user.id).order_by(LearningRecord.updated_at.desc())).all()
    return [learning_output(record) for record in records if (not project_id or record.project_id == project_id) and (not client_id or record.client_id == client_id) and (not status_filter or record.status == status_filter)]


@app.post("/api/learning", response_model=LearningRecordOut, status_code=201)
def create_learning(data: LearningRecordIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if data.project_id:
        project = owned_project(data.project_id, user, session)
        if data.client_id and data.client_id != project.client_id:
            raise HTTPException(422, "El cliente del aprendizaje no coincide con el proyecto")
    if data.client_id:
        owned_client(data.client_id, user, session)
    record = LearningRecord(owner_id=user.id, project_id=data.project_id, client_id=data.client_id, title=data.title.strip(), content=data.content.strip(), source_type=data.source_type.strip(), tags=data.tags.strip(), confidence=data.confidence.strip(), evidence_json=json.dumps(data.evidence, ensure_ascii=False))
    session.add(record); session.flush()
    create_approval_task(session, user, record.project_id, "learning", str(record.id), f"Validar aprendizaje: {record.title}", "Un aprendizaje solo pasa a la memoria reutilizable cuando una persona confirma que está suficientemente respaldado.")
    session.commit(); session.refresh(record)
    return learning_output(record)


def owned_project(project_id: UUID, user: User, session: Session) -> Project:
    statement = select(Project).where(Project.id == project_id, Project.owner_id == user.id).options(selectinload(Project.documents), selectinload(Project.evidence_items), selectinload(Project.result))
    project = session.exec(statement).first()
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    return project


def task_output(task: ProjectTask) -> ProjectTaskOut:
    return ProjectTaskOut.model_validate(task)


@app.get("/api/projects/{project_id}/tasks", response_model=list[ProjectTaskOut])
def list_project_tasks(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    tasks = session.exec(select(ProjectTask).where(ProjectTask.project_id == project_id, ProjectTask.owner_id == user.id).order_by(ProjectTask.status, ProjectTask.created_at.desc())).all()
    return [task_output(task) for task in tasks]


@app.post("/api/projects/{project_id}/tasks", response_model=ProjectTaskOut, status_code=201)
def create_project_task(project_id: UUID, data: ProjectTaskIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    task = ProjectTask(project_id=project.id, owner_id=user.id, **{key: value.strip() if isinstance(value, str) else value for key, value in data.model_dump().items()})
    project.updated_at = now(); session.add(task); session.add(project); session.commit(); session.refresh(task)
    return task_output(task)


@app.patch("/api/projects/{project_id}/tasks/{task_id}", response_model=ProjectTaskOut)
def update_project_task(project_id: UUID, task_id: UUID, data: ProjectTaskUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    task = session.get(ProjectTask, task_id)
    if not task or task.project_id != project.id or task.owner_id != user.id:
        raise HTTPException(404, "Tarea no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value.strip() if isinstance(value, str) else value)
    task.updated_at = now(); project.updated_at = now(); session.add(task); session.add(project); session.commit(); session.refresh(task)
    return task_output(task)


@app.delete("/api/projects/{project_id}/tasks/{task_id}", status_code=204)
def delete_project_task(project_id: UUID, task_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    task = session.get(ProjectTask, task_id)
    if not task or task.project_id != project.id or task.owner_id != user.id:
        raise HTTPException(404, "Tarea no encontrada")
    session.delete(task); project.updated_at = now(); session.add(project); session.commit()


def measurement_output(record: MeasurementRecord) -> MeasurementOut:
    return MeasurementOut.model_validate(record)


@app.get("/api/projects/{project_id}/measurements", response_model=list[MeasurementOut])
def list_measurements(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    return [measurement_output(record) for record in session.exec(select(MeasurementRecord).where(MeasurementRecord.project_id == project_id, MeasurementRecord.owner_id == user.id).order_by(MeasurementRecord.created_at.desc())).all()]


@app.post("/api/projects/{project_id}/measurements", response_model=MeasurementOut, status_code=201)
def create_measurement(project_id: UUID, data: MeasurementIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    record = MeasurementRecord(project_id=project.id, owner_id=user.id, **{key: value.strip() for key, value in data.model_dump().items()})
    project.updated_at = now(); session.add(record); session.add(project); session.commit(); session.refresh(record)
    return measurement_output(record)


@app.get("/api/agents", response_model=list[AgentDefinitionOut])
def list_agents(user: User = Depends(current_user)):
    return AGENT_CATALOG


@app.get("/api/projects/{project_id}/agents", response_model=list[AgentRunOut])
def list_agent_runs(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    runs = session.exec(select(AgentRun).where(AgentRun.project_id == project_id, AgentRun.owner_id == user.id).order_by(AgentRun.created_at.desc())).all()
    return [agent_run_output(run) for run in runs]


@app.post("/api/projects/{project_id}/agents/run", response_model=AgentRunOut, status_code=201)
def execute_agent(project_id: UUID, data: AgentRunIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    if data.agent_key not in {agent["key"] for agent in AGENT_CATALOG}:
        raise HTTPException(422, "Agente no disponible")
    stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
    brief = json.loads(stored_brief.data_json) if stored_brief else {"request": project.brief, "communication_goal": project.objective}
    dossier = session.exec(select(StrategyDossier).where(StrategyDossier.project_id == project.id).order_by(StrategyDossier.version.desc())).first()
    strategy = json.loads(dossier.content_json) if dossier else {}
    selected = session.exec(select(StrategyDecision).where(StrategyDecision.project_id == project.id)).first()
    decision = {"route_key": selected.route_key, "rationale": selected.rationale, "launch_plan": selected.launch_plan} if selected and dossier and selected.dossier_id == dossier.id else {}
    memory = session.exec(select(ClientMemory).where(ClientMemory.client_id == project.client_id)).first()
    memory_data = json.loads(memory.data_json) if memory else {}
    learning = [{"title": record.title, "content": record.content, "confidence": record.confidence, "tags": record.tags} for record in relevant_learning_records(project, user, session)]
    output, model = run_agent(data.agent_key, project.name, brief, strategy, decision, memory_data, learning, data.instruction.strip())
    run = AgentRun(project_id=project.id, owner_id=user.id, agent_key=data.agent_key, instruction=data.instruction.strip(), output_json=json.dumps(output, ensure_ascii=False), model_used=model)
    session.add(run); session.flush()
    agent = next(agent for agent in AGENT_CATALOG if agent["key"] == data.agent_key)
    create_approval_task(session, user, project.id, "agent_run", str(run.id), f"Revisar: {agent['name']} · {project.name}", "La salida del agente queda como borrador hasta que una persona la apruebe, pida cambios o la rechace.")
    project.workflow_stage = "desarrollo_creativo" if data.agent_key == "creative_director" else "diagnostico" if data.agent_key in {"briefing", "research", "strategy"} else project.workflow_stage
    project.updated_at = now(); session.add(project); session.commit(); session.refresh(run)
    return agent_run_output(run)


@app.get("/api/approvals", response_model=list[ApprovalTaskOut])
def list_approvals(status_filter: str = Query(default="pending"), user: User = Depends(current_user), session: Session = Depends(get_session)):
    tasks = session.exec(select(ApprovalTask).where(ApprovalTask.owner_id == user.id).order_by(ApprovalTask.created_at.desc())).all()
    return [task for task in tasks if not status_filter or task.status == status_filter]


@app.patch("/api/approvals/{task_id}", response_model=ApprovalTaskOut)
def resolve_approval(task_id: UUID, data: ApprovalResolveIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    task = session.get(ApprovalTask, task_id)
    if not task or task.owner_id != user.id:
        raise HTTPException(404, "Aprobación no encontrada")
    task.status = data.status; task.notes = data.notes.strip(); task.resolved_at = now(); session.add(task)
    if task.kind == "learning":
        record = session.get(LearningRecord, UUID(task.entity_id))
        if record:
            record.status = data.status; record.updated_at = now(); session.add(record)
    if task.kind == "agent_run":
        run = session.get(AgentRun, UUID(task.entity_id))
        if run:
            run.status = data.status; session.add(run)
    session.commit(); session.refresh(task)
    return task


def project_embedding(project: Project, session: Session) -> list[float] | None:
    signature = f"{project.name}\n{project.objective}\n{project.brief}".strip()
    stored = session.exec(select(ProjectRadarVector).where(ProjectRadarVector.project_id == project.id)).first()
    if stored and stored.signature == signature and stored.model == settings.openai_embedding_model:
        return json.loads(stored.embedding_json)
    try:
        vector = embed_text(signature)
    except Exception:
        return None
    if not vector:
        return None
    if stored:
        stored.signature = signature; stored.embedding_json = json.dumps(vector); stored.model = settings.openai_embedding_model; stored.updated_at = now()
    else:
        stored = ProjectRadarVector(project_id=project.id, signature=signature, embedding_json=json.dumps(vector), model=settings.openai_embedding_model)
    session.add(stored); session.commit()
    return vector


def sync_project_radar(project: Project, user: User, session: Session) -> list[tuple[ProjectKnowledgeLink, KnowledgeItem]]:
    items = session.exec(select(KnowledgeItem).where(KnowledgeItem.owner_id == user.id)).all()
    item_map = {item.id: item for item in items}
    vectors = session.exec(select(KnowledgeVector).where(KnowledgeVector.knowledge_item_id.in_(list(item_map)))).all() if item_map else []
    vector_map = {str(vector.knowledge_item_id): json.loads(vector.embedding_json) for vector in vectors}
    matches = relevant_matches(project, items, vector_map, project_embedding(project, session))
    links = session.exec(select(ProjectKnowledgeLink).where(ProjectKnowledgeLink.project_id == project.id)).all()
    link_map = {link.knowledge_item_id: link for link in links}
    for item, score, reason in matches:
        link = link_map.get(item.id)
        if not link:
            link = ProjectKnowledgeLink(project_id=project.id, knowledge_item_id=item.id, score=score, reason=reason)
            session.add(link); links.append(link); link_map[item.id] = link
        else:
            link.score = score; link.reason = reason; link.updated_at = now(); session.add(link)
    session.commit()
    valid = [(link, item_map[link.knowledge_item_id]) for link in links if link.knowledge_item_id in item_map]
    order = {RadarLinkStatus.approved: 0, RadarLinkStatus.suggested: 1, RadarLinkStatus.dismissed: 2}
    return sorted(valid, key=lambda pair: (order[pair[0].status], -pair[0].score))


def suggestion_output(link: ProjectKnowledgeLink, item: KnowledgeItem) -> RadarSuggestionOut:
    return RadarSuggestionOut(item=KnowledgeOut.model_validate(item), status=link.status, score=link.score, reason=link.reason)


def relevant_library_entries(project: Project, user: User, session: Session, limit: int = 6) -> list[LibraryEntry]:
    reference = f"{project.name} {project.objective} {project.brief}".lower()
    terms = {term for term in reference.replace("/", " ").split() if len(term) >= 4}
    candidates = session.exec(select(LibraryEntry).where(LibraryEntry.owner_id == user.id)).all()
    ranked: list[tuple[int, LibraryEntry]] = []
    for item in candidates:
        if item.client_id and item.client_id != project.client_id:
            continue
        text = f"{item.title} {item.description} {item.tags} {item.ai_analysis}".lower()
        overlap = sum(term in text for term in terms)
        score = overlap * 12 + (40 if item.client_id == project.client_id else 0)
        if score:
            ranked.append((score, item))
    return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(user: User = Depends(current_user), session: Session = Depends(get_session)):
    statement = select(Project).where(Project.owner_id == user.id).options(selectinload(Project.documents), selectinload(Project.evidence_items), selectinload(Project.result)).order_by(Project.updated_at.desc())
    return session.exec(statement).all()


@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    client = session.get(Client, data.client_id)
    if not client or client.owner_id != user.id:
        raise HTTPException(404, "Cliente no encontrado")
    project = Project(**data.model_dump(), owner_id=user.id)
    session.add(project); session.commit(); session.refresh(project)
    return project


@app.patch("/api/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: UUID, data: ProjectUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value.strip())
    project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    for document in project.documents:
        if document.storage_path:
            Path(document.storage_path).unlink(missing_ok=True)
    for link in session.exec(select(ProjectKnowledgeLink).where(ProjectKnowledgeLink.project_id == project.id)).all():
        session.delete(link)
    vector = session.exec(select(ProjectRadarVector).where(ProjectRadarVector.project_id == project.id)).first()
    if vector:
        session.delete(vector)
    brief=session.exec(select(ProjectBrief).where(ProjectBrief.project_id==project.id)).first()
    if brief:session.delete(brief)
    decision=session.exec(select(StrategyDecision).where(StrategyDecision.project_id==project.id)).first()
    if decision:session.delete(decision)
    for record in session.exec(select(LearningRecord).where(LearningRecord.project_id == project.id)).all(): session.delete(record)
    for task in session.exec(select(ApprovalTask).where(ApprovalTask.project_id == project.id)).all(): session.delete(task)
    for run in session.exec(select(AgentRun).where(AgentRun.project_id == project.id)).all(): session.delete(run)
    for note in session.exec(select(CreativeNote).where(CreativeNote.project_id == project.id)).all(): session.delete(note)
    for task in session.exec(select(ProjectTask).where(ProjectTask.project_id == project.id)).all(): session.delete(task)
    for measurement in session.exec(select(MeasurementRecord).where(MeasurementRecord.project_id == project.id)).all(): session.delete(measurement)
    for annotation in session.exec(select(CreativeAnnotation).where(CreativeAnnotation.project_id == project.id)).all(): session.delete(annotation)
    for draft in session.exec(select(CreativeVisualDraft).where(CreativeVisualDraft.project_id == project.id)).all():
        if draft.storage_path: Path(draft.storage_path).unlink(missing_ok=True)
        session.delete(draft)
    for plan in session.exec(select(CreativeProductionPlan).where(CreativeProductionPlan.project_id == project.id)).all(): session.delete(plan)
    for concept in session.exec(select(CreativeConcept).where(CreativeConcept.project_id == project.id)).all(): session.delete(concept)
    for d in session.exec(select(StrategyDossier).where(StrategyDossier.project_id==project.id)).all():session.delete(d)
    for c in session.exec(select(CreativeSubmission).where(CreativeSubmission.project_id==project.id)).all():
        if c.storage_path:Path(c.storage_path).unlink(missing_ok=True)
        session.delete(c)
    session.delete(project); session.commit()


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    return owned_project(project_id, user, session)

BRIEF_REQUIRED={"request":"Pedido original","business_context":"Contexto de negocio","product":"Producto o servicio","business_goal":"Objetivo de negocio","commercial_goal":"Objetivo comercial","communication_goal":"Objetivo de comunicación","audience":"Personas prioritarias","competitors":"Categoría y competencia","proof":"Razones para creer","restrictions":"Restricciones","territory":"Territorio y distribución","deadline":"Plazos"}
def brief_output(stored:ProjectBrief|None)->BriefOut:
    data=json.loads(stored.data_json) if stored else {};missing=[v for k,v in BRIEF_REQUIRED.items() if not str(data.get(k,"")).strip()];return BriefOut(data=data,completeness=stored.completeness if stored else 0,missing_required=missing)
@app.get("/api/projects/{project_id}/brief",response_model=BriefOut)
def get_project_brief(project_id:UUID,user:User=Depends(current_user),session:Session=Depends(get_session)):
    owned_project(project_id,user,session);return brief_output(session.exec(select(ProjectBrief).where(ProjectBrief.project_id==project_id)).first())
@app.put("/api/projects/{project_id}/brief",response_model=BriefOut)
def save_project_brief(project_id:UUID,data:BriefIn,user:User=Depends(current_user),session:Session=Depends(get_session)):
    p=owned_project(project_id,user,session);clean={str(k):str(v).strip() for k,v in data.data.items()};completeness=round(sum(bool(clean.get(k)) for k in BRIEF_REQUIRED)*100/len(BRIEF_REQUIRED));stored=session.exec(select(ProjectBrief).where(ProjectBrief.project_id==p.id)).first() or ProjectBrief(project_id=p.id);stored.data_json=json.dumps(clean,ensure_ascii=False);stored.completeness=completeness;stored.updated_at=now();p.brief=clean.get("request") or p.brief;p.updated_at=now();session.add(stored);session.add(p);session.commit();session.refresh(stored);return brief_output(stored)


@app.get("/api/projects/{project_id}/library-suggestions", response_model=list[LibraryOut])
def project_library_suggestions(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    return relevant_library_entries(project, user, session)


@app.get("/api/projects/{project_id}/radar", response_model=list[RadarSuggestionOut])
def project_radar(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    return [suggestion_output(link, item) for link, item in sync_project_radar(project, user, session)]


@app.patch("/api/projects/{project_id}/radar/{item_id}", response_model=RadarSuggestionOut)
def decide_project_radar(project_id: UUID, item_id: UUID, data: RadarDecisionIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    item = owned_knowledge(item_id, user, session)
    link = session.exec(select(ProjectKnowledgeLink).where(ProjectKnowledgeLink.project_id == project.id, ProjectKnowledgeLink.knowledge_item_id == item.id)).first()
    if not link:
        link = ProjectKnowledgeLink(project_id=project.id, knowledge_item_id=item.id)
    link.status = data.status; link.updated_at = now(); session.add(link); session.commit(); session.refresh(link)
    return suggestion_output(link, item)


@app.post("/api/projects/{project_id}/documents", response_model=ProjectOut, status_code=201)
async def upload_document(project_id: UUID, file: UploadFile = File(...), user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED:
        raise HTTPException(415, "Formato no admitido. Usá PDF, DOCX, TXT o Markdown.")
    data = await file.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "El archivo supera 15 MB")
    filename = safe_name(file.filename or "documento")
    document = Document(filename=filename, content_type=content_type, size=len(data), storage_path="", extracted_text=extract_text(data, content_type), project_id=project.id)
    path = Path(settings.upload_dir) / str(project.id) / f"{document.id}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    document.storage_path = str(path)
    session.add(document); project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)


@app.post("/api/projects/{project_id}/audio", response_model=ProjectOut, status_code=201)
async def upload_audio(
    project_id: UUID, file: UploadFile = File(...), context: str = Form(default="", max_length=2000),
    transcript: str = Form(default="", max_length=100000), user: User = Depends(current_user), session: Session = Depends(get_session),
):
    project = owned_project(project_id, user, session)
    filename = safe_name(file.filename or "audio")
    suffix = Path(filename).suffix.lower()
    content_type = file.content_type or "application/octet-stream"
    if content_type not in AUDIO_TYPES and suffix not in AUDIO_EXTENSIONS:
        raise HTTPException(415, "Formato no admitido. Usá MP3, MP4, M4A, WAV o WEBM.")
    data = await file.read(AUDIO_MAX_SIZE + 1)
    if len(data) > AUDIO_MAX_SIZE:
        raise HTTPException(413, "El audio supera 25 MB")
    extracted = transcript.strip()
    if not extracted:
        try: extracted = transcribe_audio(data, filename, content_type, f"Proyecto: {project.name}. {context}")
        except Exception: extracted = ""
    document = Document(filename=filename, content_type=content_type, size=len(data), storage_path="", extracted_text=extracted, project_id=project.id)
    path = Path(settings.upload_dir) / str(project.id) / f"{document.id}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); document.storage_path = str(path)
    session.add(document); project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)


@app.post("/api/projects/{project_id}/mail-file", response_model=ProjectOut, status_code=201)
async def upload_mail_file(project_id: UUID, file: UploadFile = File(...), user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    filename = safe_name(file.filename or "correo.eml")
    if Path(filename).suffix.lower() != ".eml" and file.content_type != "message/rfc822":
        raise HTTPException(415, "Formato no admitido. Guardá el correo como archivo .eml")
    data = await file.read(EMAIL_MAX_SIZE + 1)
    if len(data) > EMAIL_MAX_SIZE:
        raise HTTPException(413, "El correo supera 15 MB")
    try: extracted = extract_email(data)
    except Exception: raise HTTPException(422, "No se pudo leer el archivo de correo")
    document = Document(filename=filename, content_type="message/rfc822", size=len(data), storage_path="", extracted_text=extracted, project_id=project.id)
    path = Path(settings.upload_dir) / str(project.id) / f"{document.id}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); document.storage_path = str(path)
    session.add(document); project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)


@app.post("/api/projects/{project_id}/mail", response_model=ProjectOut, status_code=201)
def add_mail_text(project_id: UUID, data: EmailTextIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    extracted = format_email(data.subject, data.from_address, data.to_address, data.date, data.content)
    document = Document(filename=f"correo_{safe_name(data.subject)[:80]}.eml", content_type="message/rfc822", size=len(extracted.encode()), storage_path="", extracted_text=extracted, project_id=project.id)
    path = Path(settings.upload_dir) / str(project.id) / f"{document.id}.eml.txt"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(extracted, encoding="utf-8"); document.storage_path = str(path)
    session.add(document); project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)


def owned_document(project_id: UUID, document_id: UUID, user: User, session: Session) -> Document:
    project = owned_project(project_id, user, session)
    document = session.get(Document, document_id)
    if not document or document.project_id != project.id:
        raise HTTPException(404, "Fuente no encontrada")
    return document


@app.patch("/api/projects/{project_id}/documents/{document_id}/text", response_model=DocumentOut)
def update_document_text(project_id: UUID, document_id: UUID, data: DocumentTextIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    document = owned_document(project_id, document_id, user, session)
    document.extracted_text = data.text.strip(); session.add(document); session.commit(); session.refresh(document)
    return document


@app.get("/api/projects/{project_id}/documents/{document_id}/media")
def document_media(project_id: UUID, document_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    document = owned_document(project_id, document_id, user, session)
    if not document.storage_path or not Path(document.storage_path).exists():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(document.storage_path, media_type=document.content_type, filename=document.filename)


@app.delete("/api/projects/{project_id}/documents/{document_id}", status_code=204)
def delete_document(project_id: UUID, document_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    document = owned_document(project_id, document_id, user, session)
    if document.storage_path:
        Path(document.storage_path).unlink(missing_ok=True)
    project = session.get(Project, project_id)
    session.delete(document)
    if project:
        project.updated_at = now(); session.add(project)
    session.commit()


@app.post("/api/projects/{project_id}/evidence", response_model=ProjectOut, status_code=201)
def add_evidence(project_id: UUID, data: EvidenceIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    values = data.model_dump()
    values["url"] = str(values["url"]) if values["url"] else ""
    item = EvidenceItem(**values, project_id=project.id)
    session.add(item); project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)


@app.post("/api/projects/{project_id}/research", response_model=ProjectResearchOut)
def research_project(project_id: UUID, data: ProjectResearchIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    summary, sources, model = project_web_research(project.name, project.objective, data.query, active_research_domains(user, session))
    if not settings.openai_api_key:
        raise HTTPException(409, summary)
    existing_urls = {item.url for item in project.evidence_items if item.url}
    added = 0
    for source in sources:
        url = source.get("url", "")
        if not url or url in existing_urls:
            continue
        host = urlparse(url).hostname or "Fuente web"
        item = EvidenceItem(
            kind="reference", title=source.get("title") or host, url=url, source=host,
            content=f"Investigación web OLIVA. Síntesis inicial: {summary[:2500]}\n\nFuente externa por validar; no equivale a evidencia propia.",
            project_id=project.id,
        )
        session.add(item); existing_urls.add(url); added += 1
    project.updated_at = now(); session.add(project); session.commit()
    return ProjectResearchOut(summary=summary, added_sources=added, sources=sources, model_used=model)


@app.delete("/api/projects/{project_id}/evidence/{evidence_id}", status_code=204)
def delete_evidence(project_id: UUID, evidence_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    item = session.get(EvidenceItem, evidence_id)
    if not item or item.project_id != project.id:
        raise HTTPException(404, "Evidencia no encontrada")
    session.delete(item); project.updated_at = now(); session.add(project); session.commit()


@app.post("/api/projects/{project_id}/analyze", response_model=ProjectOut)
def analyze_project(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    project.status = ProjectStatus.analyzing; project.updated_at = now(); session.add(project); session.commit()
    try:
        file_context = "\n\n".join(f"ARCHIVO: {doc.filename}\n{doc.extracted_text}" for doc in project.documents)
        evidence_context = "\n\n".join(
            f"{('REFERENCIA' if item.kind.value == 'reference' else 'NOTA DEL CLIENTE')}: {item.title}\nFuente: {item.source or 'No indicada'}\nURL: {item.url or 'No aplica'}\nContenido: {item.content}"
            for item in project.evidence_items
        )
        suggestions = sync_project_radar(project, user, session)
        selected_radar = [item for link, item in suggestions if link.status == RadarLinkStatus.approved]
        client = session.get(Client, project.client_id)
        client_context = (
            f"Nombre: {client.name}\nIndustria: {client.industry or 'No definida'}\nContexto: {client.description or 'No aportado'}"
            if client else "Sin contexto de cliente"
        )
        client_memory = session.exec(select(ClientMemory).where(ClientMemory.client_id == project.client_id)).first()
        memory_context = json.loads(client_memory.data_json) if client_memory else {}
        learned = relevant_learning_records(project, user, session)
        learning_context = "\n".join(f"APRENDIZAJE CONFIRMADO: {record.title}\n{record.content}\nAlcance: {record.confidence}" for record in learned)
        library_items = relevant_library_entries(project, user, session)
        library_context = "\n\n".join(
            f"BIBLIOTECA COGNITIVA ({item.kind}): {item.title}\nFuente: {item.source or item.url or 'OLIVA'}\nAprendizaje: {item.description or item.ai_analysis[:5000]}"
            for item in library_items
        )
        source_manifest = (
            f"RESUMEN DE FUENTES: {len(project.documents)} archivos, "
            f"{len(project.evidence_items)} evidencias directas, {len(selected_radar)} señales aprobadas del Radar, {len(library_items)} referencias aplicables de la Biblioteca Cognitiva y {len(learned)} aprendizajes confirmados."
        )
        full_context=f"{source_manifest}\n\nCLIENTE:\n{client_context}\n\nMEMORIA DEL CLIENTE (no es evidencia nueva):\n{json.dumps(memory_context, ensure_ascii=False)}\n\nMARCO METODOLÓGICO OLIVA (criterio, no evidencia de cliente):\n{foundational_context()}\n\n{file_context}\n\n{evidence_context}\n\n{radar_context(selected_radar)}\n\n{library_context}\n\n{learning_context}"
        data = analyze(project, full_context, client_context)
        # StrategyResult es el resumen legado que alimenta la vista inicial; la
        # IA actual puede devolver diagnóstico estructurado. Lo preservamos sin
        # perder información, serializándolo para las columnas de texto.
        legacy_data = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value) for key, value in data.items()}
        existing = project.result
        if existing:
            for key, value in legacy_data.items():
                setattr(existing, key, value)
            session.add(existing)
        else:
            session.add(StrategyResult(project_id=project.id, **legacy_data))
        stored_brief=session.exec(select(ProjectBrief).where(ProjectBrief.project_id==project.id)).first();brief_data=json.loads(stored_brief.data_json) if stored_brief else {"request":project.brief,"communication_goal":project.objective};source_names=[d.filename for d in project.documents]+[e.title for e in project.evidence_items]+[f"Radar OLIVA: {i.title}" for i in selected_radar]+[f"Biblioteca OLIVA: {i.title}" for i in library_items]+[f"Aprendizaje OLIVA: {record.title}" for record in learned]+[f"Marco OLIVA: {reference['author']}" for reference in FOUNDATIONAL_REFERENCES];dossier_data,dossier_model=analyze_dossier(project,brief_data,full_context,source_names);previous=session.exec(select(StrategyDossier).where(StrategyDossier.project_id==project.id).order_by(StrategyDossier.version.desc())).first();dossier=StrategyDossier(project_id=project.id,version=previous.version+1 if previous else 1,content_json=json.dumps(dossier_data,ensure_ascii=False),model_used=dossier_model);session.add(dossier);session.flush()
        decision=session.exec(select(StrategyDecision).where(StrategyDecision.project_id==project.id)).first()
        if decision and dossier_data.get(decision.route_key):
            decision.dossier_id=dossier.id; decision.updated_at=now(); session.add(decision)
        create_approval_task(session,user,project.id,"strategy",str(dossier.id),f"Aprobar estrategia · {project.name}","La estrategia integra evidencia del proyecto, memoria, aprendizajes confirmados y el marco metodológico OLIVA. Revisá las rutas antes de aprobar.")
        project.status = ProjectStatus.completed
        project.workflow_stage = "estrategia"
    except Exception:
        session.rollback()
        project.status = ProjectStatus.failed
        session.add(project); session.commit()
        raise HTTPException(502, "No se pudo completar el análisis")
    project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)

def dossier_output(d:StrategyDossier)->DossierOut:return DossierOut(id=d.id,version=d.version,sections=json.loads(d.content_json),approval_status=d.approval_status,approval_notes=d.approval_notes,model_used=d.model_used,created_at=d.created_at)
@app.get("/api/projects/{project_id}/strategy",response_model=DossierOut)
def get_strategy(project_id:UUID,user:User=Depends(current_user),session:Session=Depends(get_session)):
    owned_project(project_id,user,session);d=session.exec(select(StrategyDossier).where(StrategyDossier.project_id==project_id).order_by(StrategyDossier.version.desc())).first()
    if not d:raise HTTPException(404,"El proyecto todavía no tiene un contrabrief estratégico")
    return dossier_output(d)

@app.post("/api/projects/{project_id}/strategy/expand-routes", response_model=DossierOut)
def expand_strategy_routes(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Adds deeper alternatives without recalculating or replacing the existing strategic route."""
    project = owned_project(project_id, user, session)
    current = session.exec(select(StrategyDossier).where(StrategyDossier.project_id == project_id).order_by(StrategyDossier.version.desc())).first()
    if not current:
        raise HTTPException(404, "El proyecto todavía no tiene estrategia")
    current_sections = json.loads(current.content_json)
    if all(current_sections.get(f"ruta_{number}") for number in range(1, 8)):
        return dossier_output(current)
    stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
    brief_data = json.loads(stored_brief.data_json) if stored_brief else {"request": project.brief, "communication_goal": project.objective}
    source_names = [document.filename for document in project.documents] + [item.title for item in project.evidence_items]
    expanded = local_dossier(project, brief_data, source_names)
    for number in range(4, 8):
        current_sections[f"ruta_{number}"] = expanded[f"ruta_{number}"]
    current_sections["comparacion_de_rutas"] = expanded["comparacion_de_rutas"]
    next_version = StrategyDossier(project_id=project.id, version=current.version + 1, content_json=json.dumps(current_sections, ensure_ascii=False), model_used=f"{current.model_used} · rutas ampliadas")
    session.add(next_version); session.flush()
    decision = session.exec(select(StrategyDecision).where(StrategyDecision.project_id == project.id)).first()
    if decision and current_sections.get(decision.route_key):
        decision.dossier_id = next_version.id; decision.updated_at = now(); session.add(decision)
        next_version.approval_status = current.approval_status
        next_version.approval_notes = f"{current.approval_notes} Alternativas ampliadas sin alterar la ruta elegida.".strip()
    session.add(next_version); session.commit(); session.refresh(next_version)
    return dossier_output(next_version)
@app.patch("/api/projects/{project_id}/strategy/approval",response_model=DossierOut)
def approve_strategy(project_id:UUID,data:ApprovalIn,user:User=Depends(current_user),session:Session=Depends(get_session)):
    owned_project(project_id,user,session)
    if data.status not in {"approved","changes","rejected","pending_information"}:raise HTTPException(422,"Estado inválido")
    d=session.exec(select(StrategyDossier).where(StrategyDossier.project_id==project_id).order_by(StrategyDossier.version.desc())).first()
    if not d:raise HTTPException(404,"El proyecto todavía no tiene estrategia")
    decision = session.exec(select(StrategyDecision).where(StrategyDecision.project_id == project_id)).first()
    if data.status == "approved" and (not decision or decision.dossier_id != d.id):
        raise HTTPException(409,"Elegí una ruta estratégica de trabajo antes de aprobar la estrategia")
    d.approval_status=data.status;d.approval_notes=data.notes.strip();d.updated_at=now();session.add(d)
    task=session.exec(select(ApprovalTask).where(ApprovalTask.kind=="strategy",ApprovalTask.entity_id==str(d.id),ApprovalTask.owner_id==user.id,ApprovalTask.status=="pending")).first()
    if task: task.status=data.status;task.notes=data.notes.strip();task.resolved_at=now();session.add(task)
    project=session.get(Project, project_id)
    if project and data.status=="approved": project.workflow_stage="ruta_seleccionada";project.updated_at=now();session.add(project)
    session.commit();session.refresh(d);return dossier_output(d)


@app.get("/api/projects/{project_id}/strategy/decision", response_model=StrategyDecisionOut)
def get_strategy_decision(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    decision = session.exec(select(StrategyDecision).where(StrategyDecision.project_id == project_id)).first()
    dossier = session.exec(select(StrategyDossier).where(StrategyDossier.project_id == project_id).order_by(StrategyDossier.version.desc())).first()
    if not decision or not dossier:
        raise HTTPException(404, "Todavía no se eligió una ruta estratégica")
    if decision.dossier_id != dossier.id:
        sections = json.loads(dossier.content_json)
        if not sections.get(decision.route_key):
            raise HTTPException(404, "La ruta elegida no existe en la estrategia vigente")
        decision.dossier_id = dossier.id; decision.updated_at = now(); session.add(decision); session.commit(); session.refresh(decision)
    return decision


@app.put("/api/projects/{project_id}/strategy/decision", response_model=StrategyDecisionOut)
def save_strategy_decision(project_id: UUID, data: StrategyDecisionIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    dossier = session.exec(select(StrategyDossier).where(StrategyDossier.project_id == project_id).order_by(StrategyDossier.version.desc())).first()
    if not dossier:
        raise HTTPException(404, "El proyecto todavía no tiene estrategia")
    sections = json.loads(dossier.content_json)
    if not sections.get(data.route_key):
        raise HTTPException(422, "La ruta elegida no existe en la estrategia vigente")
    decision = session.exec(select(StrategyDecision).where(StrategyDecision.project_id == project_id)).first()
    if decision:
        decision.dossier_id = dossier.id; decision.route_key = data.route_key; decision.rationale = data.rationale.strip(); decision.launch_plan = data.launch_plan.strip(); decision.updated_at = now()
    else:
        decision = StrategyDecision(project_id=project_id, dossier_id=dossier.id, route_key=data.route_key, rationale=data.rationale.strip(), launch_plan=data.launch_plan.strip())
    decision.dossier_id = dossier.id
    dossier.approval_status = "approved"; dossier.approval_notes = "Ruta de trabajo confirmada al guardar la decisión estratégica."; dossier.updated_at = now()
    task = session.exec(select(ApprovalTask).where(ApprovalTask.kind == "strategy", ApprovalTask.entity_id == str(dossier.id), ApprovalTask.owner_id == user.id, ApprovalTask.status == "pending")).first()
    if task:
        task.status = "approved"; task.notes = dossier.approval_notes; task.resolved_at = now(); session.add(task)
    project.workflow_stage = "ruta_seleccionada"; project.updated_at = now()
    session.add(decision); session.add(dossier); session.add(project); session.commit(); session.refresh(decision)
    return decision


def creative_concept_output(concept: CreativeConcept) -> CreativeConceptOut:
    return CreativeConceptOut(id=concept.id, project_id=concept.project_id, dossier_id=concept.dossier_id, decision_id=concept.decision_id, title=concept.title, content=json.loads(concept.content_json), status=concept.status, model_used=concept.model_used, created_at=concept.created_at, updated_at=concept.updated_at)


def approved_creative_context(project: Project, user: User, session: Session) -> tuple[StrategyDossier, StrategyDecision]:
    dossier = session.exec(select(StrategyDossier).where(StrategyDossier.project_id == project.id).order_by(StrategyDossier.version.desc())).first()
    decision = session.exec(select(StrategyDecision).where(StrategyDecision.project_id == project.id)).first()
    if not dossier or dossier.approval_status != "approved" or not decision or decision.dossier_id != dossier.id:
        raise HTTPException(409, "Primero confirmá una estrategia y su ruta de trabajo antes de pasar a creatividad")
    return dossier, decision


@app.get("/api/projects/{project_id}/creative-concepts", response_model=list[CreativeConceptOut])
def list_creative_concepts(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    concepts = session.exec(select(CreativeConcept).where(CreativeConcept.project_id == project_id, CreativeConcept.owner_id == user.id).order_by(CreativeConcept.updated_at.desc())).all()
    return [creative_concept_output(concept) for concept in concepts]


@app.post("/api/projects/{project_id}/creative-concepts/generate", response_model=CreativeConceptOut, status_code=201)
def generate_creative_concept_board(project_id: UUID, data: CreativeConceptGenerateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    dossier, decision = approved_creative_context(project, user, session)
    stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
    brief = json.loads(stored_brief.data_json) if stored_brief else {"request": project.brief, "communication_goal": project.objective}
    memory = session.exec(select(ClientMemory).where(ClientMemory.client_id == project.client_id)).first()
    content, model = generate_creative_concepts(project.name, brief, json.loads(dossier.content_json), {"route_key": decision.route_key, "rationale": decision.rationale, "launch_plan": decision.launch_plan}, json.loads(memory.data_json) if memory else {}, data.instruction.strip())
    concept = CreativeConcept(project_id=project.id, dossier_id=dossier.id, decision_id=decision.id, owner_id=user.id, title="Plataformas creativas propuestas", content_json=json.dumps(content, ensure_ascii=False), model_used=model)
    session.add(concept); session.commit(); session.refresh(concept)
    return creative_concept_output(concept)


@app.patch("/api/projects/{project_id}/creative-concepts/{concept_id}", response_model=CreativeConceptOut)
def update_creative_concept(project_id: UUID, concept_id: UUID, data: CreativeConceptUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    dossier, decision = approved_creative_context(project, user, session)
    concept = session.get(CreativeConcept, concept_id)
    if not concept or concept.project_id != project.id or concept.owner_id != user.id:
        raise HTTPException(404, "Plataforma creativa no encontrada")
    was_selected = concept.status == "selected"
    concept.content_json = json.dumps(data.content, ensure_ascii=False); concept.status = data.status; concept.dossier_id = dossier.id; concept.decision_id = decision.id; concept.updated_at = now()
    if data.status == "selected" and not was_selected:
        stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
        brief = json.loads(stored_brief.data_json) if stored_brief else {"request": project.brief, "communication_goal": project.objective, "territory": project.territory}
        plan_content, plan_model = generate_campaign_plan(project.name, brief, {"route_key": decision.route_key, "rationale": decision.rationale, "launch_plan": decision.launch_plan}, data.content, str(data.content.get("selected_territory_id", "")))
        plan = session.exec(select(CreativeProductionPlan).where(CreativeProductionPlan.concept_id == concept.id)).first()
        if plan:
            plan.content_json = json.dumps(plan_content, ensure_ascii=False); plan.status = "draft"; plan.model_used = plan_model; plan.updated_at = now()
        else:
            plan = CreativeProductionPlan(project_id=project.id, concept_id=concept.id, owner_id=user.id, content_json=json.dumps(plan_content, ensure_ascii=False), model_used=plan_model)
        project.workflow_stage = "plan_de_campana"; project.updated_at = now(); session.add(plan); session.add(project)
    session.add(concept); session.commit(); session.refresh(concept)
    return creative_concept_output(concept)


def creative_plan_output(plan: CreativeProductionPlan) -> CreativeProductionPlanOut:
    return CreativeProductionPlanOut(id=plan.id, project_id=plan.project_id, concept_id=plan.concept_id, content=json.loads(plan.content_json), status=plan.status, model_used=plan.model_used, created_at=plan.created_at, updated_at=plan.updated_at)


def creative_note_output(note: CreativeNote) -> CreativeNoteOut:
    return CreativeNoteOut.model_validate(note)


@app.get("/api/projects/{project_id}/creative-plans", response_model=list[CreativeProductionPlanOut])
def list_creative_plans(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    selected = session.exec(select(CreativeConcept).where(CreativeConcept.project_id == project.id, CreativeConcept.owner_id == user.id, CreativeConcept.status == "selected").order_by(CreativeConcept.updated_at.desc())).first()
    plan = session.exec(select(CreativeProductionPlan).where(CreativeProductionPlan.concept_id == selected.id)).first() if selected else None
    if selected and not plan:
        _, decision = approved_creative_context(project, user, session)
        stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
        brief = json.loads(stored_brief.data_json) if stored_brief else {"request": project.brief, "communication_goal": project.objective, "territory": project.territory}
        board = json.loads(selected.content_json)
        content, model = generate_campaign_plan(project.name, brief, {"route_key": decision.route_key, "rationale": decision.rationale, "launch_plan": decision.launch_plan}, board, str(board.get("selected_territory_id", "")))
        plan = CreativeProductionPlan(project_id=project.id, concept_id=selected.id, owner_id=user.id, content_json=json.dumps(content, ensure_ascii=False), model_used=model)
        session.add(plan); session.commit()
    plans = session.exec(select(CreativeProductionPlan).where(CreativeProductionPlan.project_id == project_id, CreativeProductionPlan.owner_id == user.id).order_by(CreativeProductionPlan.updated_at.desc())).all()
    return [creative_plan_output(plan) for plan in plans]


@app.patch("/api/projects/{project_id}/creative-plans/{plan_id}", response_model=CreativeProductionPlanOut)
def update_creative_plan(project_id: UUID, plan_id: UUID, data: CreativeProductionPlanUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    plan = session.get(CreativeProductionPlan, plan_id)
    if not plan or plan.project_id != project.id or plan.owner_id != user.id:
        raise HTTPException(404, "Plan de campaña no encontrado")
    was_approved = plan.status == "approved"
    content = dict(data.content)
    if data.status == "approved":
        # La generación sucede una sola vez, al aprobar por primera vez. A partir
        # de entonces cada cambio pertenece al equipo y se guarda sin reescribirlo.
        if not was_approved and not content.get("propuestas_de_produccion"):
            concept = session.get(CreativeConcept, plan.concept_id)
            if not concept or concept.project_id != project.id or concept.owner_id != user.id:
                raise HTTPException(409, "No se encontró la plataforma creativa que sustenta este plan")
            stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
            brief = json.loads(stored_brief.data_json) if stored_brief else {"request": project.brief, "communication_goal": project.objective, "territory": project.territory}
            production, model = generate_production_proposals(project.name, brief, json.loads(concept.content_json), content)
            for key, value in production.items():
                if key not in content:
                    content[key] = value
            plan.model_used = model
        project.workflow_stage = "produccion_creativa"; project.updated_at = now(); session.add(project)
    plan.content_json = json.dumps(content, ensure_ascii=False); plan.status = data.status; plan.updated_at = now(); session.add(plan)
    session.commit(); session.refresh(plan)
    return creative_plan_output(plan)


@app.get("/api/projects/{project_id}/creative-notes", response_model=list[CreativeNoteOut])
def list_creative_notes(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    notes = session.exec(select(CreativeNote).where(CreativeNote.project_id == project_id, CreativeNote.owner_id == user.id).order_by(CreativeNote.updated_at.desc())).all()
    return [creative_note_output(note) for note in notes]


@app.post("/api/projects/{project_id}/creative-notes", response_model=CreativeNoteOut, status_code=201)
def create_creative_note(project_id: UUID, data: CreativeNoteIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    selected = session.exec(select(CreativeConcept).where(CreativeConcept.project_id == project.id, CreativeConcept.owner_id == user.id, CreativeConcept.status == "selected").order_by(CreativeConcept.updated_at.desc())).first()
    note = CreativeNote(project_id=project.id, concept_id=selected.id if selected else None, owner_id=user.id, kind=data.kind, author=data.author.strip(), content=data.content.strip())
    project.updated_at = now(); session.add(note); session.add(project); session.commit(); session.refresh(note)
    return creative_note_output(note)


@app.patch("/api/projects/{project_id}/creative-notes/{note_id}", response_model=CreativeNoteOut)
def update_creative_note(project_id: UUID, note_id: UUID, data: CreativeNoteUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    note = session.get(CreativeNote, note_id)
    if not note or note.project_id != project_id or note.owner_id != user.id:
        raise HTTPException(404, "Aporte creativo no encontrado")
    note.status = data.status; note.updated_at = now(); session.add(note); session.commit(); session.refresh(note)
    return creative_note_output(note)


@app.get("/api/projects/{project_id}/creative-table", response_model=list[AgentRunOut])
def list_creative_table_runs(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    runs = session.exec(select(AgentRun).where(AgentRun.project_id == project_id, AgentRun.owner_id == user.id, AgentRun.agent_key == "creative_table").order_by(AgentRun.created_at.desc())).all()
    return [agent_run_output(run) for run in runs]


@app.post("/api/projects/{project_id}/creative-table", response_model=AgentRunOut, status_code=201)
def run_creative_table(project_id: UUID, data: CreativeTableIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    dossier, decision = approved_creative_context(project, user, session)
    concept = session.exec(select(CreativeConcept).where(CreativeConcept.project_id == project.id, CreativeConcept.owner_id == user.id, CreativeConcept.status == "selected").order_by(CreativeConcept.updated_at.desc())).first()
    if not concept:
        raise HTTPException(409, "Elegí una plataforma creativa antes de convocar la Mesa OLIVA")
    plan = session.exec(select(CreativeProductionPlan).where(CreativeProductionPlan.concept_id == concept.id, CreativeProductionPlan.owner_id == user.id)).first()
    stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
    brief = json.loads(stored_brief.data_json) if stored_brief else {"request": project.brief, "communication_goal": project.objective}
    output, model = creative_table(project.name, brief, {"route_key": decision.route_key, "rationale": decision.rationale, "launch_plan": decision.launch_plan}, json.loads(concept.content_json), json.loads(plan.content_json) if plan else {}, data.question.strip())
    run = AgentRun(project_id=project.id, owner_id=user.id, agent_key="creative_table", instruction=data.question.strip(), output_json=json.dumps(output, ensure_ascii=False), status="draft", model_used=model)
    project.updated_at = now(); session.add(run); session.add(project); session.commit(); session.refresh(run)
    return agent_run_output(run)


@app.get("/api/projects/{project_id}/creative-plans/{plan_id}/production-package", response_model=ProductionPackageOut)
def production_package(project_id: UUID, plan_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    plan = session.get(CreativeProductionPlan, plan_id)
    if not plan or plan.project_id != project.id or plan.owner_id != user.id:
        raise HTTPException(404, "Plan de campaña no encontrado")
    if plan.status != "approved":
        raise HTTPException(409, "Aprobá el plan de campaña antes de emitir el paquete de producción")
    content = json.loads(plan.content_json); base = content.get("base_aprobada", {}) if isinstance(content, dict) else {}
    assets = session.exec(select(BrandAsset).where(BrandAsset.client_id == project.client_id, BrandAsset.owner_id == user.id).order_by(BrandAsset.created_at.desc())).all()
    deliverables = []
    for item in content.get("propuestas_de_produccion", []) if isinstance(content, dict) else []:
        if isinstance(item, dict):
            deliverables.append({"pieza": str(item.get("pieza", "Pieza")), "formato": str(item.get("duracion_formato") or item.get("medio") or "Por definir"), "objetivo": str(item.get("objetivo", "")), "guion": str(item.get("guion", "")), "produccion": str(item.get("produccion", ""))})
    return ProductionPackageOut(
        campaign=str(base.get("plataforma", "Campaña aprobada")), status="listo para coordinación", strategy=str(base.get("idea_central", "")), deliverables=deliverables,
        assets=[f"{asset.label}: {asset.filename}" for asset in assets] or ["Logo, packaging y paleta final: pendientes de carga o confirmación."],
        confirmations=[str(value) for value in content.get("faltantes_de_produccion", [])] or ["Confirmar responsables, materiales finales, derechos y disponibilidad antes de producir."],
        handoff=["Asignar responsable y fecha a cada pieza.", "Usar el guion editable como base; los cambios no recalculan la estrategia.", "Subir cada material terminado para revisión contra estrategia, marca y propiedad.", "Registrar resultados y aprobación humana al cierre para convertirlos en aprendizaje."],
    )


def creative_visual_output(draft: CreativeVisualDraft) -> CreativeVisualOut:
    return CreativeVisualOut(id=draft.id, project_id=draft.project_id, plan_id=draft.plan_id, title=draft.title, prompt=draft.prompt, status=draft.status, model_used=draft.model_used, created_at=draft.created_at)


@app.get("/api/projects/{project_id}/creative-visuals", response_model=list[CreativeVisualOut])
def list_creative_visuals(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    drafts = session.exec(select(CreativeVisualDraft).where(CreativeVisualDraft.project_id == project_id, CreativeVisualDraft.owner_id == user.id, CreativeVisualDraft.status != "archived").order_by(CreativeVisualDraft.created_at.desc())).all()
    # Retira los marcadores técnicos de una versión anterior: nunca fueron arte ni
    # deben ocupar el lugar de un boceto real solicitado por el equipo.
    legacy = [draft for draft in drafts if "boceto compositivo" in draft.model_used.lower()]
    for draft in legacy:
        if draft.storage_path:
            Path(draft.storage_path).unlink(missing_ok=True)
        session.delete(draft)
    if legacy:
        session.commit()
        drafts = [draft for draft in drafts if draft not in legacy]
    return [creative_visual_output(draft) for draft in drafts]


@app.post("/api/projects/{project_id}/creative-plans/{plan_id}/visuals/generate", response_model=CreativeVisualOut, status_code=201)
def generate_creative_visual(project_id: UUID, plan_id: UUID, data: CreativeVisualGenerateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    plan = session.get(CreativeProductionPlan, plan_id)
    if not plan or plan.project_id != project.id or plan.owner_id != user.id:
        raise HTTPException(404, "Plan de campaña no encontrado")
    concept = session.get(CreativeConcept, plan.concept_id)
    if not concept or concept.owner_id != user.id:
        raise HTTPException(409, "Elegí una plataforma creativa antes de generar un boceto")
    if not settings.openai_api_key:
        raise HTTPException(503, "No se generó ningún boceto: falta configurar una clave de API de OpenAI con acceso a generación de imágenes.")
    plan_content = json.loads(plan.content_json); board = json.loads(concept.content_json)
    stored_brief = session.exec(select(ProjectBrief).where(ProjectBrief.project_id == project.id)).first()
    brief_data = json.loads(stored_brief.data_json) if stored_brief else {}
    base = plan_content.get("base_aprobada", {}); assets = session.exec(select(BrandAsset).where(BrandAsset.client_id == project.client_id, BrandAsset.owner_id == user.id).order_by(BrandAsset.created_at.desc())).all()
    palette = next((asset.palette for asset in assets if asset.palette.strip()), "#153F35 verde profundo, #D9FF43 lima, #F4F1E9 papel cálido")
    # El primer boceto no se "encarga": nace de la idea aprobada. Las direcciones
    # sugeridas por el plan sólo se usan para enriquecer esa lectura, nunca para
    # volver a pedir al usuario que decida qué visualizar.
    visual_directions = plan_content.get("bocetos_visuales", [])
    first_direction = visual_directions[0] if isinstance(visual_directions, list) and visual_directions and isinstance(visual_directions[0], dict) else {}
    selected_id = str(board.get("selected_territory_id", "")) if isinstance(board, dict) else ""
    selected_territory = next((item for item in board.get("territorios", []) if isinstance(item, dict) and str(item.get("id", "")) == selected_id), {}) if isinstance(board, dict) else {}
    campaign_name = str(selected_territory.get("nombre") or base.get("plataforma") or "Campaña aprobada")
    automatic = data.title == "Boceto de dirección de arte" and not data.focus.strip() and not data.visual_style.strip()
    title = f"Boceto maestro — {campaign_name}" if automatic else data.title.strip()
    focus = (str(first_direction.get("prompt_de_produccion") or first_direction.get("direccion") or selected_territory.get("idea_central") or base.get("idea_central") or "la idea central aprobada") if automatic else data.focus.strip())
    visual_style = (str(selected_territory.get("estilo") or selected_territory.get("tono") or "dirección de arte derivada de la plataforma creativa aprobada") if automatic else data.visual_style.strip())
    scripts = plan_content.get("propuestas_de_produccion", [])
    script_continuity = "; ".join(str(item.get("pieza", "")) for item in scripts[:5] if isinstance(item, dict))
    category_context = str(brief_data.get("category") or brief_data.get("industry") or brief_data.get("market_context") or "")
    competitor_context = str(brief_data.get("competitors") or brief_data.get("competitive_context") or "")
    prompt = (OLIVA_ART_DIRECTION_STANDARD + "\n"
        "Create one high-end advertising campaign key visual / previsualization for an agency team. "
        f"Campaign: {campaign_name}. Approved idea: {selected_territory.get('idea_central') or base.get('idea_central', '')}. "
        f"Human tension: {selected_territory.get('tension') or ''}. Brand role: {selected_territory.get('rol_de_marca') or ''}. "
        f"Territory: {base.get('territorio', '')}. Format: {data.format}. Creative focus derived from the approved campaign: {focus}. Visual direction: {visual_style}. "
        f"Mandatory continuity: preserve the approved campaign, its prior scripts ({script_continuity}), category context ({category_context}) and competitive frame ({competitor_context}). Do not invent a different campaign, product positioning, target or visual territory. "
        f"The visual scene and creative idea must dominate; use OLIVA Publicidad presentation language only as a subtle framing system: warm paper, deep forest green and acid-lime accents, restrained editorial craft. Palette: {palette}. "
        "Never render any text, letters, numbers, maps, logos, labels, packaging names, prices, arrows or fake annotations inside the image. Do not create a moodboard or presentation board. Avoid generic stock advertising, clichés and watermarks. The OLIVA interface will apply the real branding and typography outside the image."
    )
    try:
        from openai import OpenAI
        response = OpenAI(api_key=settings.openai_api_key).images.generate(model=settings.openai_image_model, prompt=prompt, size="1536x1024", quality="medium", output_format="png")
        encoded = response.data[0].b64_json
        if not encoded:
            raise RuntimeError("La imagen no llegó en el formato esperado")
        raw = base64.b64decode(encoded)
    except Exception as exc:
        raise HTTPException(503, "No se generó ningún boceto. La cuenta de OpenAI no tiene cuota disponible para imágenes o la clave no tiene acceso a gpt-image-1.") from exc
    draft = CreativeVisualDraft(project_id=project.id, plan_id=plan.id, owner_id=user.id, title=title, prompt=prompt, storage_path="", content_type="image/png", status="generated", model_used=settings.openai_image_model)
    path = Path(settings.upload_dir) / "creative-visuals" / str(project.id) / f"{draft.id}.png"; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw); draft.storage_path = str(path)
    session.add(draft); session.commit(); session.refresh(draft)
    return creative_visual_output(draft)

@app.patch("/api/projects/{project_id}/creative-visuals/{draft_id}", response_model=CreativeVisualOut)
def update_creative_visual(project_id: UUID, draft_id: UUID, data: CreativeVisualUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    draft = session.get(CreativeVisualDraft, draft_id)
    if not draft or draft.project_id != project_id or draft.owner_id != user.id:
        raise HTTPException(404, "Boceto visual no encontrado")
    if data.title is not None: draft.title = data.title.strip()
    if data.status is not None: draft.status = data.status
    session.add(draft); session.commit(); session.refresh(draft)
    return creative_visual_output(draft)


@app.get("/api/projects/{project_id}/creative-visuals/{draft_id}/media")
def creative_visual_media(project_id: UUID, draft_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    draft = session.get(CreativeVisualDraft, draft_id)
    if not draft or draft.project_id != project_id or draft.owner_id != user.id or not Path(draft.storage_path).exists():
        raise HTTPException(404, "Boceto visual no encontrado")
    return FileResponse(draft.storage_path, media_type=draft.content_type, filename=f"{safe_name(draft.title)}.png")


def creative_output(i:CreativeSubmission)->CreativeOut:return CreativeOut(id=i.id,project_id=i.project_id,name=i.name,medium=i.medium,rationale=i.rationale,filename=i.filename,content_type=i.content_type,size=i.size,verdict=i.verdict,scores=json.loads(i.score_json),evaluation=i.evaluation,model_used=i.model_used,created_at=i.created_at)
def creative_annotation_output(annotation: CreativeAnnotation) -> CreativeAnnotationOut:
    return CreativeAnnotationOut.model_validate(annotation)
@app.get("/api/projects/{project_id}/creative",response_model=list[CreativeOut])
def list_creative(project_id:UUID,user:User=Depends(current_user),session:Session=Depends(get_session)):
    owned_project(project_id,user,session);return [creative_output(i) for i in session.exec(select(CreativeSubmission).where(CreativeSubmission.project_id==project_id).order_by(CreativeSubmission.created_at.desc())).all()]
@app.get("/api/projects/{project_id}/creative/{creative_id}/annotations", response_model=list[CreativeAnnotationOut])
def list_creative_annotations(project_id: UUID, creative_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    creative = session.get(CreativeSubmission, creative_id)
    if not creative or creative.project_id != project_id or creative.owner_id != user.id:
        raise HTTPException(404, "Material no encontrado")
    annotations = session.exec(select(CreativeAnnotation).where(CreativeAnnotation.creative_submission_id == creative.id, CreativeAnnotation.owner_id == user.id).order_by(CreativeAnnotation.created_at.desc())).all()
    return [creative_annotation_output(annotation) for annotation in annotations]


@app.post("/api/projects/{project_id}/creative/{creative_id}/annotations", response_model=CreativeAnnotationOut, status_code=201)
def create_creative_annotation(project_id: UUID, creative_id: UUID, data: CreativeAnnotationIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    creative = session.get(CreativeSubmission, creative_id)
    if not creative or creative.project_id != project_id or creative.owner_id != user.id:
        raise HTTPException(404, "Material no encontrado")
    annotation = CreativeAnnotation(creative_submission_id=creative.id, project_id=project_id, owner_id=user.id, **data.model_dump())
    session.add(annotation); session.commit(); session.refresh(annotation)
    return creative_annotation_output(annotation)


@app.patch("/api/projects/{project_id}/creative/{creative_id}/annotations/{annotation_id}", response_model=CreativeAnnotationOut)
def update_creative_annotation(project_id: UUID, creative_id: UUID, annotation_id: UUID, data: CreativeAnnotationUpdateIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned_project(project_id, user, session)
    annotation = session.get(CreativeAnnotation, annotation_id)
    if not annotation or annotation.project_id != project_id or annotation.creative_submission_id != creative_id or annotation.owner_id != user.id:
        raise HTTPException(404, "Observación no encontrada")
    annotation.status = data.status; annotation.updated_at = now(); session.add(annotation); session.commit(); session.refresh(annotation)
    return creative_annotation_output(annotation)
@app.post("/api/projects/{project_id}/creative",response_model=CreativeOut,status_code=201)
async def review_creative(project_id:UUID,file:UploadFile=File(...),name:str=Form(...,min_length=2,max_length=250),medium:str=Form(default="",max_length=250),rationale:str=Form(default="",max_length=10000),user:User=Depends(current_user),session:Session=Depends(get_session)):
    p=owned_project(project_id,user,session);d,decision=approved_creative_context(p,user,session)
    concept=session.exec(select(CreativeConcept).where(CreativeConcept.project_id==p.id,CreativeConcept.owner_id==user.id,CreativeConcept.status=="selected").order_by(CreativeConcept.updated_at.desc())).first()
    if not concept:raise HTTPException(409,"Primero elegí y guardá una plataforma creativa. Después podés cargar materiales para revisión.")
    ct=file.content_type or "application/octet-stream"
    if ct not in PHOTO_TYPES|{"application/pdf","text/plain","text/markdown"}:raise HTTPException(415,"Usá JPG, PNG, WEBP, PDF o texto")
    raw=await file.read(MAX_SIZE+1)
    if len(raw)>MAX_SIZE:raise HTTPException(413,"La pieza supera 15 MB")
    filename=safe_name(file.filename or "pieza");item=CreativeSubmission(project_id=p.id,name=name.strip(),medium=medium.strip(),rationale=rationale.strip(),filename=filename,storage_path="",content_type=ct,size=len(raw),owner_id=user.id);path=Path(settings.upload_dir)/"creative"/str(p.id)/f"{item.id}_{filename}";path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);item.storage_path=str(path);client=session.get(Client,p.client_id);strategy_data=json.loads(d.content_json);strategy_data["decision_estrategica"]={"ruta":decision.route_key,"fundamento":decision.rationale,"plan_de_lanzamiento":decision.launch_plan};strategy_data["plataforma_creativa_elegida"]=json.loads(concept.content_json);plan=session.exec(select(CreativeProductionPlan).where(CreativeProductionPlan.concept_id==concept.id,CreativeProductionPlan.owner_id==user.id)).first();strategy_data["plan_de_campana"]=json.loads(plan.content_json) if plan else {};ev=evaluate_creative(path,ct,item.name,item.medium,item.rationale,strategy_data,f"{client.name if client else ''}: {client.description if client else ''}");item.verdict=ev.get("verdict","pending");item.score_json=json.dumps(ev.get("scores",{}));item.evaluation=ev.get("evaluation","");item.model_used=ev.get("model_used","OLIVA Creative Review");session.add(item);session.flush();create_approval_task(session,user,p.id,"creative_review",str(item.id),f"Revisar propuesta creativa: {item.name}","Validá si la pieza responde a la plataforma creativa elegida y la ruta aprobada antes de convertir su devolución en aprendizaje.");p.workflow_stage="desarrollo_creativo";p.updated_at=now();session.add(p);session.commit();session.refresh(item);return creative_output(item)
@app.get("/api/projects/{project_id}/creative/{creative_id}/media")
def creative_media(project_id:UUID,creative_id:UUID,user:User=Depends(current_user),session:Session=Depends(get_session)):
    owned_project(project_id,user,session);item=session.get(CreativeSubmission,creative_id)
    if not item or item.project_id!=project_id or item.owner_id!=user.id or not Path(item.storage_path).exists():raise HTTPException(404,"Pieza no encontrada")
    return FileResponse(item.storage_path,media_type=item.content_type,filename=item.filename)


@app.post("/api/projects/{project_id}/creative/{creative_id}/learning", response_model=LearningRecordOut, status_code=201)
def turn_creative_review_into_learning(project_id: UUID, creative_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    creative = session.get(CreativeSubmission, creative_id)
    if not creative or creative.project_id != project.id or creative.owner_id != user.id:
        raise HTTPException(404, "Propuesta no encontrada")
    record = LearningRecord(owner_id=user.id, project_id=project.id, client_id=project.client_id, title=f"Aprendizaje creativo: {creative.name}", content=creative.evaluation or "La propuesta requiere una devolución humana antes de registrar un aprendizaje.", source_type="creative_review", tags=f"creatividad, {creative.medium}", confidence="por_validar", evidence_json=json.dumps([f"Propuesta: {creative.filename}", f"Veredicto OLIVA: {creative.verdict}"], ensure_ascii=False))
    session.add(record); session.flush(); create_approval_task(session,user,project.id,"learning",str(record.id),f"Validar aprendizaje: {record.title}","Confirmá o corregí este aprendizaje antes de que se reutilice en proyectos futuros.");session.commit();session.refresh(record)
    return learning_output(record)


@app.get("/api/projects/{project_id}/report")
def export_project_report(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    dossier=session.exec(select(StrategyDossier).where(StrategyDossier.project_id==project.id).order_by(StrategyDossier.version.desc())).first()
    if not project.result and not dossier:
        raise HTTPException(409, "El proyecto todavía no tiene un diagnóstico para descargar")
    client = session.get(Client, project.client_id)
    approved_links = session.exec(
        select(ProjectKnowledgeLink).where(
            ProjectKnowledgeLink.project_id == project.id,
            ProjectKnowledgeLink.status == RadarLinkStatus.approved,
        )
    ).all()
    radar_items = [session.get(KnowledgeItem, link.knowledge_item_id) for link in approved_links]
    library_items = relevant_library_entries(project, user, session)
    decision = session.exec(select(StrategyDecision).where(StrategyDecision.project_id == project.id)).first()
    if decision and dossier and decision.dossier_id != dossier.id:
        decision = None
    sources = [f"- Archivo: {document.filename}" for document in project.documents]
    sources += [f"- {item.title}: {item.url or item.source or 'Nota interna'}" for item in project.evidence_items]
    sources += [f"- Radar OLIVA: {item.title} — {item.url or item.source}" for item in radar_items if item]
    sources += [f"- Biblioteca Cognitiva OLIVA: {item.title} — {item.url or item.source or 'Referencia interna'}" for item in library_items]
    result = project.result
    sections=json.loads(dossier.content_json) if dossier else {}
    full_strategy="\n\n".join(f"## {key.replace('_',' ').title()}\n\n{json.dumps(value,ensure_ascii=False,indent=2) if isinstance(value,(dict,list)) else value}" for key,value in sections.items())
    if not full_strategy and result:
        full_strategy=f"## Diagnóstico\n\n{result.diagnosis}\n\n## Evidencia\n\n{result.evidence}\n\n## Contradicciones\n\n{result.contradictions}\n\n## Hipótesis a refutar\n\n{result.hypotheses}\n\n## Pregunta estratégica\n\n{result.strategic_question}"
    report = f"""# Diagnóstico estratégico — {project.name}

**Cliente:** {client.name if client else 'No disponible'}

**Industria:** {(client.industry if client else '') or 'No definida'}

**Estado:** {dossier.approval_status if dossier else 'sin aprobación'}

**Versión:** {dossier.version if dossier else 1}

**Modelo:** {dossier.model_used if dossier else result.model_used}

**Fecha:** {(dossier.created_at if dossier else result.created_at).strftime('%d/%m/%Y %H:%M')} UTC

## Objetivo declarado

{project.objective or 'No definido'}

{f'''## Ruta de trabajo elegida

**Ruta:** {decision.route_key.replace('_', ' ').title()}

**Fundamento:** {decision.rationale}

**Plan de lanzamiento:** {decision.launch_plan}
''' if decision else ''}

{full_strategy}

## Fuentes consideradas

{chr(10).join(sources) or '- No se incorporaron fuentes adicionales.'}
"""
    filename = f"diagnostico_oliva_{project.id}.md"
    return Response(report, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
