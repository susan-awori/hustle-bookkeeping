from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single place secrets are read. Missing required values abort startup."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret: str = Field(alias="JWT_SECRET")
    phone_hash_pepper: str = Field(alias="PHONE_HASH_PEPPER")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    elevenlabs_voice_id: str = Field(default="JBFqnCBsd6RMkjVDRZzb", alias="ELEVENLABS_VOICE_ID")
    anthropic_model: str = Field(default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    audio_storage_path: str = Field(default="./storage/audio", alias="AUDIO_STORAGE_PATH")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    access_token_minutes: int = Field(default=15, alias="ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=7, alias="REFRESH_TOKEN_DAYS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_algorithm: str = "HS256"

    @model_validator(mode="after")
    def reject_placeholder_or_empty_secrets(self) -> "Settings":
        required = {
            "DATABASE_URL": self.database_url,
            "JWT_SECRET": self.jwt_secret,
            "PHONE_HASH_PEPPER": self.phone_hash_pepper,
        }
        if self.environment == "production":
            required["ELEVENLABS_API_KEY"] = self.elevenlabs_api_key
            required["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        missing = [name for name, value in required.items() if not (value and str(value).strip())]
        if missing:
            raise RuntimeError(f"Missing required secrets (set them in the environment): {', '.join(missing)}")
        weak = []
        if self.jwt_secret.startswith("replace-") or len(self.jwt_secret) < 32:
            weak.append("JWT_SECRET must be a random string of at least 32 characters")
        if self.phone_hash_pepper.startswith("replace-") or len(self.phone_hash_pepper) < 32:
            weak.append("PHONE_HASH_PEPPER must be a random string of at least 32 characters")
        if self.environment == "production":
            for name, value in (
                ("ELEVENLABS_API_KEY", self.elevenlabs_api_key),
                ("ANTHROPIC_API_KEY", self.anthropic_api_key),
            ):
                if value.startswith("replace-") or not value.strip():
                    weak.append(f"{name} must be set to a real key in production")
        if weak:
            raise RuntimeError("; ".join(weak))
        return self

    @property
    def cors_origin_list(self) -> list[str]:
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
