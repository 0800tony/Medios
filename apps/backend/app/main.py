from contextlib import asynccontextmanager
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
from .knowledge import PHOTO_MAX_SIZE, PHOTO_TYPES, analyze_photo, index_text, radar_context, relevant_items
from .models import Client, Document, EvidenceItem, KnowledgeItem, KnowledgeKind, Project, ProjectStatus, StrategyResult, User, now
from .schemas import ClientIn, ClientOut, EvidenceIn, KnowledgeLinkIn, KnowledgeOut, LoginIn, ProjectIn, ProjectOut, RegisterIn, TokenOut, UserOut
from .strategy import analyze

settings = get_settings()


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
    item = KnowledgeItem(**values, owner_id=user.id, ai_summary=data.notes, index_status="manual")
    item.indexed_text = index_text(item)
    session.add(item); session.commit(); session.refresh(item)
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
    return item


def owned_knowledge(item_id: UUID, user: User, session: Session) -> KnowledgeItem:
    item = session.get(KnowledgeItem, item_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(404, "Elemento del Radar no encontrado")
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
    session.delete(item); session.commit()


def owned_project(project_id: UUID, user: User, session: Session) -> Project:
    statement = select(Project).where(Project.id == project_id, Project.owner_id == user.id).options(selectinload(Project.documents), selectinload(Project.evidence_items), selectinload(Project.result))
    project = session.exec(statement).first()
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    return project


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


@app.get("/api/projects/{project_id}/radar", response_model=list[KnowledgeOut])
def project_radar(project_id: UUID, user: User = Depends(current_user), session: Session = Depends(get_session)):
    project = owned_project(project_id, user, session)
    items = session.exec(select(KnowledgeItem).where(KnowledgeItem.owner_id == user.id)).all()
    return relevant_items(project, items)


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
        knowledge = session.exec(select(KnowledgeItem).where(KnowledgeItem.owner_id == user.id)).all()
        selected_radar = relevant_items(project, knowledge)
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
