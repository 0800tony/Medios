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


class ClientOut(ClientIn):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    client_id: UUID
    brief: str = ""
    objective: str = ""


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


class KnowledgeLinkIn(BaseModel):
    kind: KnowledgeKind
    title: str = Field(min_length=2, max_length=250)
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
    client_id: UUID
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentOut] = []
    evidence_items: list[EvidenceOut] = []
    result: Optional[ResultOut] = None
    model_config = ConfigDict(from_attributes=True)
