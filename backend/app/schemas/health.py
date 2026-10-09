from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    service: str = Field(default="ChainGuard")
    version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    blockchain_provider: str = Field(default="demo")
    demo_mode: bool = Field(default=False)
    real_mode: bool = Field(default=False)
    operational_chains: list[str] = Field(default_factory=lambda: ["ethereum", "polygon"])
    architectural_chains: list[str] = Field(default_factory=lambda: ["bitcoin", "tron", "bsc", "solana"])
    ai_provider: str = Field(default="none")
    ai_configured: bool = Field(default=False)
    ai_model: str | None = Field(default=None)
