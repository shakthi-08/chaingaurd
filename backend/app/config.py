from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChainGuard"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    demo_mode: bool = False
    ai_provider: str = "none"
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    database_url: str = "sqlite:///./chainguard.db"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://chaingaurd.vercel.app"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
