from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeaComplaint(Base):
    """Integration-ready complaint intake. Not a live NCRP/SAHYOG connector."""

    __tablename__ = "lea_complaints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    complaint_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    wallet_address: Mapped[str] = mapped_column(String(255), nullable=False)
    blockchain: Mapped[str] = mapped_column(String(64), nullable=False)
    incident_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reported_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    investigation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="accepted", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
