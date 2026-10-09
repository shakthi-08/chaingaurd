from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    complaint_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="open", nullable=False)
    current_stage: Mapped[str] = mapped_column(String(64), default="CREATED", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    wallets: Mapped[list["Wallet"]] = relationship(back_populates="case")
    reports: Mapped[list["Report"]] = relationship(back_populates="case")
