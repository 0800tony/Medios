from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine
from .config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    # El MVP se instaló antes de que el expediente incorporara estos campos.
    # Esta migración aditiva conserva proyectos existentes en Docker/PostgreSQL.
    if engine.dialect.name == "postgresql":
        columns = {
            "workflow_stage": "VARCHAR NOT NULL DEFAULT 'ingreso'",
            "group_company": "VARCHAR NOT NULL DEFAULT 'Oliva Publicidad'",
            "participants": "VARCHAR NOT NULL DEFAULT ''",
            "territory": "VARCHAR NOT NULL DEFAULT ''",
            "deadline": "VARCHAR NOT NULL DEFAULT ''",
            "budget": "VARCHAR NOT NULL DEFAULT ''",
            "confidentiality": "VARCHAR NOT NULL DEFAULT 'interno'",
        }
        with engine.begin() as connection:
            for name, definition in columns.items():
                connection.execute(text(f"ALTER TABLE project ADD COLUMN IF NOT EXISTS {name} {definition}"))


def get_session():
    with Session(engine) as session:
        yield session
