from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator
from .models import EvidenceKind, KnowledgeKind, ProjectStatus, RadarLinkStatus


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserUpdateIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    current_password: str = ""
    new_password: str = Field(default="", min_length=0, max_length=128)

    @model_validator(mode="after")
    def validate_password_change(self):
        if self.new_password and len(self.new_password) < 8:
            raise ValueError("La nueva contraseña debe tener al menos 8 caracteres")
        if self.new_password and not self.current_password:
            raise ValueError("Ingresá tu contraseña actual")
        return self


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ClientIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    industry: str = ""
    description: str = ""


class ClientUpdateIn(ClientIn):
    pass


class ClientOut(ClientIn):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    client_id: UUID
    brief: str = ""
    objective: str = ""
    group_company: str = "Oliva Publicidad"
    participants: str = ""
    territory: str = ""
    deadline: str = ""
    budget: str = ""
    confidentiality: str = "interno"


class ProjectUpdateIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    brief: str = ""
    objective: str = ""
    workflow_stage: str = "ingreso"
    group_company: str = "Oliva Publicidad"
    participants: str = ""
    territory: str = ""
    deadline: str = ""
    budget: str = ""
    confidentiality: str = "interno"


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size: int
    category: str
    processed: bool
    text_excerpt: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentTextIn(BaseModel):
    text: str = Field(min_length=2, max_length=100000)


class EmailTextIn(BaseModel):
    subject: str = Field(min_length=2, max_length=300)
    from_address: str = Field(default="", max_length=300)
    to_address: str = Field(default="", max_length=500)
    date: str = Field(default="", max_length=100)
    content: str = Field(min_length=2, max_length=100000)


class EvidenceIn(BaseModel):
    kind: EvidenceKind
    title: str = Field(min_length=2, max_length=250)
    url: Optional[HttpUrl] = None
    source: str = Field(default="", max_length=250)
    content: str = Field(default="", max_length=20000)

    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind == EvidenceKind.reference and not self.url:
            raise ValueError("Una referencia debe incluir un enlace")
        if self.kind == EvidenceKind.client_note and not self.content.strip():
            raise ValueError("Una nota debe incluir información del cliente")
        return self


class EvidenceOut(BaseModel):
    id: UUID
    kind: EvidenceKind
    title: str
    url: str
    source: str
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectResearchIn(BaseModel):
    query: str = Field(min_length=3, max_length=600)


class ProjectResearchOut(BaseModel):
    summary: str
    added_sources: int
    sources: list[dict[str, str]]
    model_used: str


class KnowledgeLinkIn(BaseModel):
    kind: KnowledgeKind
    title: str = Field(default="", max_length=250)
    url: HttpUrl
    source: str = Field(default="", max_length=250)
    notes: str = Field(default="", max_length=20000)
    tags: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_link_kind(self):
        if self.kind not in (KnowledgeKind.article, KnowledgeKind.video):
            raise ValueError("Este formulario admite artículos o videos")
        return self


class KnowledgeOut(BaseModel):
    id: UUID
    kind: KnowledgeKind
    title: str
    url: str
    source: str
    notes: str
    tags: str
    content_type: str
    size: int
    ai_summary: str
    ai_observations: str
    index_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RadarDecisionIn(BaseModel):
    status: RadarLinkStatus

    @model_validator(mode="after")
    def validate_status(self):
        if self.status == RadarLinkStatus.suggested:
            raise ValueError("Elegí aplicar o descartar la sugerencia")
        return self


class RadarSuggestionOut(BaseModel):
    item: KnowledgeOut
    status: RadarLinkStatus
    score: int
    reason: str


class ResultOut(BaseModel):
    id: UUID
    diagnosis: str
    evidence: str
    hypotheses: str
    contradictions: str
    strategic_question: str
    confidence: str
    model_used: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectOut(BaseModel):
    id: UUID
    name: str
    brief: str
    objective: str
    status: ProjectStatus
    workflow_stage: str
    group_company: str
    participants: str
    territory: str
    deadline: str
    budget: str
    confidentiality: str
    client_id: UUID
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentOut] = []
    evidence_items: list[EvidenceOut] = []
    result: Optional[ResultOut] = None
    model_config = ConfigDict(from_attributes=True)

class BriefIn(BaseModel): data: dict[str, str]
class BriefOut(BaseModel):
    data: dict[str, str]; completeness: int; missing_required: list[str]
class ApprovalIn(BaseModel):
    status: str; notes: str = Field(default="", max_length=10000)
class DossierOut(BaseModel):
    id: UUID; version: int; sections: dict[str, object]; approval_status: str; approval_notes: str; model_used: str; created_at: datetime
class StrategyDecisionIn(BaseModel):
    route_key: str = Field(pattern="^ruta_[123]$")
    rationale: str = Field(min_length=12, max_length=10000)
    launch_plan: str = Field(min_length=12, max_length=10000)
class StrategyDecisionOut(BaseModel):
    id: UUID; project_id: UUID; dossier_id: UUID; route_key: str; rationale: str; launch_plan: str; created_at: datetime; updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
class LibraryLinkIn(BaseModel):
    kind: str; url: HttpUrl; description: str = Field(default="", max_length=20000); tags: str = Field(default="", max_length=1000); client_id: Optional[UUID] = None; results: str = Field(default="", max_length=5000)
class LibraryOut(BaseModel):
    id: UUID; kind: str; title: str; url: str; source: str; description: str; tags: str; year: str; festival: str; award: str; results: str; client_id: Optional[UUID]; content_type: str; size: int; ai_analysis: str; created_at: datetime
    model_config = ConfigDict(from_attributes=True)
class FestivalSearchIn(BaseModel): query: str = Field(min_length=3, max_length=500)
class CreativeOut(BaseModel):
    id: UUID; project_id: UUID; name: str; medium: str; rationale: str; filename: str; content_type: str; size: int; verdict: str; scores: dict[str, int]; evaluation: str; model_used: str; created_at: datetime


class CreativeConceptGenerateIn(BaseModel):
    instruction: str = Field(default="", max_length=6000)


class CreativeConceptUpdateIn(BaseModel):
    content: dict[str, object]
    status: str = Field(default="draft", pattern="^(draft|selected|rejected)$")


class CreativeConceptOut(BaseModel):
    id: UUID; project_id: UUID; dossier_id: UUID; decision_id: UUID; title: str; content: dict[str, object]; status: str; model_used: str; created_at: datetime; updated_at: datetime


class CreativeProductionPlanUpdateIn(BaseModel):
    content: dict[str, object]
    status: str = Field(default="draft", pattern="^(draft|approved)$")


class CreativeProductionPlanOut(BaseModel):
    id: UUID; project_id: UUID; concept_id: UUID; content: dict[str, object]; status: str; model_used: str; created_at: datetime; updated_at: datetime


class BrandAssetOut(BaseModel):
    id: UUID; client_id: UUID; label: str; filename: str; content_type: str; size: int; palette: str; created_at: datetime


class CreativeVisualOut(BaseModel):
    id: UUID; project_id: UUID; plan_id: UUID; title: str; prompt: str; status: str; model_used: str; created_at: datetime


class CreativeVisualGenerateIn(BaseModel):
    title: str = Field(default="Boceto de dirección de arte", min_length=3, max_length=180)
    focus: str = Field(default="", max_length=3000)


class ClientMemoryIn(BaseModel):
    data: dict[str, str]


class ClientMemoryOut(BaseModel):
    id: UUID
    client_id: UUID
    data: dict[str, str]
    version: int
    updated_at: datetime


class LearningRecordIn(BaseModel):
    title: str = Field(min_length=3, max_length=250)
    content: str = Field(min_length=12, max_length=20000)
    source_type: str = Field(default="observation", max_length=80)
    tags: str = Field(default="", max_length=1000)
    confidence: str = Field(default="por_validar", max_length=80)
    project_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    evidence: list[str] = []


class LearningRecordOut(BaseModel):
    id: UUID; project_id: Optional[UUID]; client_id: Optional[UUID]; title: str; content: str; source_type: str; tags: str; confidence: str; status: str; evidence: list[str]; created_at: datetime; updated_at: datetime


class ApprovalResolveIn(BaseModel):
    status: str = Field(pattern="^(approved|changes|rejected)$")
    notes: str = Field(default="", max_length=10000)


class ApprovalTaskOut(BaseModel):
    id: UUID; project_id: Optional[UUID]; kind: str; entity_id: str; title: str; summary: str; status: str; notes: str; created_at: datetime; resolved_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class AgentRunIn(BaseModel):
    agent_key: str = Field(min_length=3, max_length=80)
    instruction: str = Field(default="", max_length=10000)


class AgentRunOut(BaseModel):
    id: UUID; project_id: UUID; agent_key: str; instruction: str; output: dict[str, object]; status: str; model_used: str; created_at: datetime


class AgentDefinitionOut(BaseModel):
    key: str; name: str; stage: str; description: str
