from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator
from .models import EvidenceKind, ProjectStatus


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


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
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


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
