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
    openai_model: str = "gpt-5.6"
    openai_search_model: str = "gpt-5.6"
    openai_vision_model: str = "gpt-5.6-terra"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "gpt-transcribe"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
