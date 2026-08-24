from __future__ import annotations

from sqlalchemy import Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    known_wallet: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    chain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_reliability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    attributions: Mapped[list["Attribution"]] = relationship(back_populates="entity")
