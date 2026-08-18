from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OLIVA Intelligence"
    database_url: str = "sqlite:///./oliva.db"
    secret_key: str = "dev-secret-change-me"
    access_token_minutes: int = 480
    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "uploads"
    openai_api_key: str = ""
    # Se mantienen perfiles separados para que la calidad máxima se use donde
    # decide el negocio y no se desperdicie en tareas operativas repetitivas.
    openai_model: str = "gpt-5.6-sol"  # compatibilidad con instalaciones anteriores
    openai_strategy_model: str = "gpt-5.6-sol"
    openai_creative_model: str = "gpt-5.6-sol"
    openai_operations_model: str = "gpt-5.6-terra"
    openai_search_model: str = "gpt-5.6-terra"
    openai_vision_model: str = "gpt-5.6-terra"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "gpt-transcribe"
    openai_image_model: str = "gpt-image-1"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
