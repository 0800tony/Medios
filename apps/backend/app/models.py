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
    workflow_stage: str = Field(default="ingreso", index=True)
    group_company: str = "Oliva Publicidad"
    participants: str = ""
    territory: str = ""
    deadline: str = ""
    budget: str = ""
    confidentiality: str = "interno"
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

class ProjectBrief(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", unique=True, index=True)
    data_json: str = "{}"
    completeness: int = 0
    updated_at: datetime = Field(default_factory=now)

class StrategyDossier(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    version: int = 1
    content_json: str = "{}"
    approval_status: str = "draft"
    approval_notes: str = ""
    model_used: str = "OLIVA Strategy — modo local"
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class StrategyDecision(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", unique=True, index=True)
    dossier_id: UUID = Field(index=True)
    route_key: str
    rationale: str = ""
    launch_plan: str = ""
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class LibraryEntry(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    kind: str = Field(index=True)
    title: str
    url: str = ""; source: str = ""; description: str = ""; tags: str = ""
    year: str = ""; festival: str = ""; award: str = ""; results: str = ""
    client_id: Optional[UUID] = Field(default=None, foreign_key="client.id", index=True)
    storage_path: str = ""; content_type: str = ""; size: int = 0; ai_analysis: str = ""
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=now)


class ResearchSource(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("owner_id", "url", name="uq_research_source_owner_url"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    name: str
    url: str
    domain: str = Field(index=True)
    country: str = "Global"
    topic: str = "general"
    description: str = ""
    priority: int = Field(default=1, index=True)
    active: bool = Field(default=True, index=True)
    is_foundational: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=now)

class CreativeSubmission(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    name: str; medium: str = ""; rationale: str = ""
    filename: str; storage_path: str; content_type: str; size: int = 0
    verdict: str = "pending"; score_json: str = "{}"; evaluation: str = ""
    model_used: str = "OLIVA Creative Review — modo local"
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=now)


class CreativeConcept(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    dossier_id: UUID = Field(index=True)
    decision_id: UUID = Field(index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    title: str = "Plataformas creativas"
    content_json: str = "{}"
    status: str = Field(default="draft", index=True)
    model_used: str = "OLIVA Creative Director — guía local"
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class CreativeProductionPlan(SQLModel, table=True):
    """The editable bridge between an approved creative platform and production."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    concept_id: UUID = Field(foreign_key="creativeconcept.id", unique=True, index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    content_json: str = "{}"
    status: str = Field(default="draft", index=True)
    model_used: str = "OLIVA Campaign Planner — guía local"
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class BrandAsset(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    label: str
    filename: str
    storage_path: str
    content_type: str
    size: int = 0
    palette: str = ""
    created_at: datetime = Field(default_factory=now)


class CreativeVisualDraft(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    plan_id: UUID = Field(foreign_key="creativeproductionplan.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    title: str
    prompt: str
    storage_path: str = ""
    content_type: str = "image/png"
    status: str = Field(default="draft", index=True)
    model_used: str = "OLIVA Art Director"
    created_at: datetime = Field(default_factory=now)


class CreativeNote(SQLModel, table=True):
    """A human contribution to a campaign. It never triggers regeneration."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    concept_id: Optional[UUID] = Field(default=None, foreign_key="creativeconcept.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    kind: str = Field(default="idea", index=True)
    author: str = "Equipo OLIVA"
    content: str
    status: str = Field(default="open", index=True)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class ProjectTask(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    title: str
    description: str = ""
    assignee: str = ""
    stage: str = Field(default="estrategia", index=True)
    status: str = Field(default="pending", index=True)
    priority: str = Field(default="media", index=True)
    due_date: str = ""
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class CreativeAnnotation(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    creative_submission_id: UUID = Field(foreign_key="creativesubmission.id", index=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    author: str = "Equipo OLIVA"
    comment: str
    x: float = 50
    y: float = 50
    status: str = Field(default="open", index=True)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class MeasurementRecord(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    metric: str
    value: str
    baseline: str = ""
    target: str = ""
    period: str = ""
    source: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=now)


class MarketWatch(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    client_id: Optional[UUID] = Field(default=None, foreign_key="client.id", index=True)
    name: str
    query: str
    kind: str = Field(default="competitor", index=True)
    active: bool = Field(default=True, index=True)
    last_summary: str = ""
    last_sources_json: str = "[]"
    last_checked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=now)


class ClientMemory(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id", unique=True, index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    data_json: str = "{}"
    version: int = 1
    updated_at: datetime = Field(default_factory=now)


class LearningRecord(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    project_id: Optional[UUID] = Field(default=None, foreign_key="project.id", index=True)
    client_id: Optional[UUID] = Field(default=None, foreign_key="client.id", index=True)
    title: str
    content: str
    source_type: str = "observation"
    tags: str = ""
    confidence: str = "por_validar"
    status: str = Field(default="proposed", index=True)
    evidence_json: str = "[]"
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class ApprovalTask(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    project_id: Optional[UUID] = Field(default=None, foreign_key="project.id", index=True)
    kind: str = Field(index=True)
    entity_id: str = ""
    title: str
    summary: str = ""
    status: str = Field(default="pending", index=True)
    notes: str = ""
    created_at: datetime = Field(default_factory=now)
    resolved_at: Optional[datetime] = None


class AgentRun(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    owner_id: UUID = Field(foreign_key="user.id", index=True)
    agent_key: str = Field(index=True)
    instruction: str = ""
    output_json: str = "{}"
    status: str = Field(default="draft", index=True)
    model_used: str = "OLIVA OS — modo local"
    created_at: datetime = Field(default_factory=now)
