from __future__ import annotations

from sqlalchemy import Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskIndicator(Base):
    __tablename__ = "risk_indicators"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), default="medium", nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    transaction_refs: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    wallet_addresses: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    evidence_refs: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
