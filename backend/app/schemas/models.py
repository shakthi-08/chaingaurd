from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CaseCreate(BaseModel):
    case_id: str = Field(..., min_length=1, max_length=128)
    complaint_ref: str | None = Field(default=None, max_length=255)
    status: str = Field(default="open", max_length=64)
    created_at: datetime


class WalletCreate(BaseModel):
    address: str = Field(..., min_length=1, max_length=255)
    chain: str = Field(..., min_length=1, max_length=64)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    labels: list[str] | None = None

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, labels):
        if labels is None:
            return None
        return [str(label).strip() for label in labels if str(label).strip()]


class TransactionCreate(BaseModel):
    tx_hash: str = Field(..., min_length=1, max_length=255)
    from_address: str = Field(..., min_length=1, max_length=255)
    to_address: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1, max_length=255)
    token: str | None = Field(default=None, max_length=64)
    timestamp: datetime
    block: int | None = None


class GraphEdgeCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=255)
    destination: str = Field(..., min_length=1, max_length=255)
    tx_ref: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime


class EntityCreate(BaseModel):
    entity_id: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=128)


class AttributionCreate(BaseModel):
    wallet: str = Field(..., min_length=1, max_length=255)
    entity: str = Field(..., min_length=1, max_length=128)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] | None = None
    source: str | None = Field(default=None, max_length=128)

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, reasons):
        if reasons is None:
            return None
        return [str(reason).strip() for reason in reasons if str(reason).strip()]


class RiskIndicatorCreate(BaseModel):
    type: str = Field(..., min_length=1, max_length=128)
    score: float = Field(..., ge=0.0, le=1.0)
    evidence_ref: str | None = Field(default=None, max_length=255)


class FindingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    severity: str = Field(..., min_length=1, max_length=64)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str | None = Field(default=None, max_length=255)


class EvidenceCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., min_length=1, max_length=64)
    source: str | None = Field(default=None, max_length=255)
    hash: str | None = Field(default=None, max_length=255)
    timestamp: datetime


class ReportCreate(BaseModel):
    report_id: str = Field(..., min_length=1, max_length=128)
    case_id: str = Field(..., min_length=1, max_length=128)
    generated_at: datetime
    version: str = Field(default="1.0", max_length=64)
