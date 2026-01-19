from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
        description="Comma-separated list of allowed origins.",
    )

    request_timeout_seconds: float = Field(default=60.0, alias="REQUEST_TIMEOUT_SECONDS")

    max_upload_mb: int = Field(default=200, alias="MAX_UPLOAD_MB")
    trim_silence_default: bool = Field(default=True, alias="TRIM_SILENCE_DEFAULT")
    speechmatics_language: str = Field(default="en", alias="SPEECHMATICS_LANG")

    speechmatics_base_url: str = Field(default="https://asr.api.speechmatics.com", alias="SPEECHMATICS_BASE_URL")
    speechmatics_api_key: str = Field(default="", alias="SPEECHMATICS_API_KEY")
    speechmatics_poll_interval_seconds: float = Field(default=2.0, alias="SPEECHMATICS_POLL_INTERVAL_SECONDS")
    speechmatics_poll_timeout_seconds: float = Field(default=900.0, alias="SPEECHMATICS_POLL_TIMEOUT_SECONDS")

    openai_base_url: str = Field(default="https://api.openai.com", alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-nano", alias="OPENAI_MODEL")

    @property
    def cors_allow_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

