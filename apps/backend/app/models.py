from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectStatus(str, Enum):
    draft = "draft"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class EvidenceKind(str, Enum):
    reference = "reference"
    client_note = "client_note"


class KnowledgeKind(str, Enum):
    article = "article"
    video = "video"
    photo = "photo"


class RadarLinkStatus(str, Enum):
    suggested = "suggested"
    approved = "approved"
    dismissed = "dismissed"


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    password_hash: str
    created_at: datetime = Field(default_factory=now)


class Client(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    industry: str = ""
    description: str = ""
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=now)
    projects: List["Project"] = Relationship(back_populates="client", cascade_delete=True)


class Project(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    brief: str = ""
    objective: str = ""
    status: ProjectStatus = Field(default=ProjectStatus.draft)
    client_id: UUID = Field(foreign_key="client.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
    client: Optional[Client] = Relationship(back_populates="projects")
    documents: List["Document"] = Relationship(back_populates="project", cascade_delete=True)
    evidence_items: List["EvidenceItem"] = Relationship(back_populates="project", cascade_delete=True)
    result: Optional["StrategyResult"] = Relationship(back_populates="project", cascade_delete=True)


class Document(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str
    content_type: str
    size: int
    storage_path: str
    extracted_text: str = ""
    project_id: UUID = Field(foreign_key="project.id", index=True)
    created_at: datetime = Field(default_factory=now)
    project: Optional[Project] = Relationship(back_populates="documents")

    @property
    def processed(self) -> bool:
        return bool(self.extracted_text.strip())

    @property
    def text_excerpt(self) -> str:
        text = " ".join(self.extracted_text.split())
        return text[:400]

    @property
    def category(self) -> str:
        if self.content_type.startswith("audio/") or self.content_type == "video/mp4":
            return "audio"
        if self.content_type == "message/rfc822":
            return "email"
        return "document"


class EvidenceItem(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    kind: EvidenceKind = Field(index=True)
    title: str
    url: str = ""
    source: str = ""
    content: str = ""
    project_id: UUID = Field(foreign_key="project.id", index=True)
    created_at: datetime = Field(default_factory=now)
    project: Optional[Project] = Relationship(back_populates="evidence_items")


class KnowledgeItem(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    kind: KnowledgeKind = Field(index=True)
    title: str
    url: str = ""
    source: str = ""
    notes: str = ""
    tags: str = ""
    storage_path: str = ""
    content_type: str = ""
    size: int = 0
    ai_summary: str = ""
    ai_observations: str = ""
    indexed_text: str = ""
    index_status: str = "manual"
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=now)


class KnowledgeVector(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    knowledge_item_id: UUID = Field(foreign_key="knowledgeitem.id", unique=True, index=True)
    embedding_json: str
    model: str
    updated_at: datetime = Field(default_factory=now)


class ProjectRadarVector(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", unique=True, index=True)
    signature: str
    embedding_json: str
    model: str
    updated_at: datetime = Field(default_factory=now)


class ProjectKnowledgeLink(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("project_id", "knowledge_item_id", name="uq_project_knowledge"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    knowledge_item_id: UUID = Field(foreign_key="knowledgeitem.id", index=True)
    status: RadarLinkStatus = Field(default=RadarLinkStatus.suggested, index=True)
    score: int = 0
    reason: str = ""
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class StrategyResult(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", unique=True, index=True)
    diagnosis: str
    evidence: str
    hypotheses: str
    contradictions: str
    strategic_question: str
    confidence: str = "media"
    model_used: str = "OLIVA Strategy — modo local"
    created_at: datetime = Field(default_factory=now)
    project: Optional[Project] = Relationship(back_populates="result")
