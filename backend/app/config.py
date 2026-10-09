from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChainGuard"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    demo_mode: bool = False
    blockchain_provider: str = "demo"
    etherscan_api_key: str | None = None
    polygonscan_api_key: str | None = None
    blockchain_api_timeout: int = 30
    blockchain_page_size: int = 200
    blockchain_max_pages: int = 1
    ai_provider: str = "none"
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    ai_timeout: int = 60
    database_url: str = "sqlite:///./chainguard.db"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://chaingaurd.vercel.app"
    cors_origin_regex: str = r"^https://chaingaurd-[a-z0-9]+-darweb\.vercel\.app$"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


def is_demo_mode_enabled() -> bool:
    return bool(settings.demo_mode) or settings.environment.strip().lower() == "demo"


def is_real_mode_enabled() -> bool:
    provider = (settings.blockchain_provider or "").strip().lower()
    return provider == "real"
