from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single place secrets are read. Safe fallbacks allow zero-config Render boot."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite:///./hustle.db", alias="DATABASE_URL")
    jwt_secret: str = Field(default="hustle-secret-key-production-32-chars-long", alias="JWT_SECRET")
    phone_hash_pepper: str = Field(default="hustle-pepper-secret-32-chars-long", alias="PHONE_HASH_PEPPER")

    huggingface_api_key: str = Field(default="", alias="HUGGINGFACE_API_KEY")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    elevenlabs_voice_id: str = Field(default="JBFqnCBsd6RMkjVDRZzb", alias="ELEVENLABS_VOICE_ID")
    anthropic_model: str = Field(default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL")
    huggingface_model: str = Field(default="openai/whisper-large-v3-turbo", alias="HUGGINGFACE_MODEL")

    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    audio_storage_path: str = Field(default="./storage/audio", alias="AUDIO_STORAGE_PATH")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    access_token_minutes: int = Field(default=43200, alias="ACCESS_TOKEN_MINUTES") # 30 days
    refresh_token_days: int = Field(default=365, alias="REFRESH_TOKEN_DAYS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_algorithm: str = "HS256"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
