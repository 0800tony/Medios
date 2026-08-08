from contextlib import asynccontextmanager
import json
from pathlib import Path
from uuid import UUID
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from .auth import create_token, current_user, hash_password, verify_password
from .config import get_settings
from .database import create_db_and_tables, get_session
from .documents import ALLOWED, MAX_SIZE, extract_text, safe_name
from .ingestion import AUDIO_EXTENSIONS, AUDIO_MAX_SIZE, AUDIO_TYPES, EMAIL_MAX_SIZE, extract_email, format_email, transcribe_audio
from .knowledge import PHOTO_MAX_SIZE, PHOTO_TYPES, analyze_photo, embed_text, index_text, radar_context, relevant_matches
from .link_reader import read_link
from .models import Client, Document, EvidenceItem, KnowledgeItem, KnowledgeKind, KnowledgeVector, Project, ProjectKnowledgeLink, ProjectRadarVector, ProjectStatus, RadarLinkStatus, StrategyResult, User, now
from .schemas import ClientIn, ClientOut, DocumentOut, DocumentTextIn, EmailTextIn, EvidenceIn, KnowledgeLinkIn, KnowledgeOut, LoginIn, ProjectIn, ProjectOut, RadarDecisionIn, RadarSuggestionOut, RegisterIn, TokenOut, UserOut, UserUpdateIn
from .strategy import analyze

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


def owned_project(project_id: UUID, user: User, session: Session) -> Project:
    statement = select(Project).where(Project.id == project_id, Project.owner_id == user.id).options(selectinload(Project.documents), selectinload(Project.evidence_items), selectinload(Project.result))
    project = session.exec(statement).first()
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    return project


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


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    return owned_project(project_id, user, session)


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
    path = Path(settings.upload_dir) / str(project.id) / filename
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    document = Document(filename=filename, content_type=content_type, size=len(data), storage_path=str(path), extracted_text=extract_text(data, content_type), project_id=project.id)
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


@app.post("/api/projects/{project_id}/evidence", response_model=ProjectOut, status_code=201)
def add_evidence(project_id: UUID, data: EvidenceIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    values = data.model_dump()
    values["url"] = str(values["url"]) if values["url"] else ""
    item = EvidenceItem(**values, project_id=project.id)
    session.add(item); project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)


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
        data = analyze(project, f"{file_context}\n\n{evidence_context}\n\n{radar_context(selected_radar)}")
        existing = project.result
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            session.add(existing)
        else:
            session.add(StrategyResult(project_id=project.id, **data))
        project.status = ProjectStatus.completed
    except Exception:
        project.status = ProjectStatus.failed
        session.add(project); session.commit()
        raise HTTPException(502, "No se pudo completar el análisis")
    project.updated_at = now(); session.add(project); session.commit()
    return owned_project(project_id, user, session)
