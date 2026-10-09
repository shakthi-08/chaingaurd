from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvestigationAlert(Base):
    __tablename__ = "investigation_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(String(1000), nullable=False)
    wallet_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_refs: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
