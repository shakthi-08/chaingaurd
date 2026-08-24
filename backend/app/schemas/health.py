from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    service: str = Field(default="ChainGuard")
    version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
